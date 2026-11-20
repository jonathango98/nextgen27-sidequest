import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf
from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.routes.player import scan
from app.services import qr
from app.services.game_state import set_state
from tests.conftest import seed_fake_players

FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=0)  # fake data (ENG-047)
VENDOR = "/static/js/vendor"
SCANNER_FILES = (
    f"{VENDOR}/barcode-detector-3.2.2.ponyfill.js",
    f"{VENDOR}/zxing-wasm-3.1.3-reader.wasm",
    "/static/js/scanner.js",
)


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    # Start the app, so pages can read the game state for the paused note (UI-033).
    with TestClient(app) as c:
        yield c


def test_arch_025_scan_page_uses_configured_format(client):
    html = client.get("/scan").text
    assert f'data-format="{load_config()["qr"]["format_version"]}"' in html


def test_ui_037_scan_page_has_camera_view_and_help_line(client):
    html = client.get("/scan").text
    assert "<video" in html
    assert 'class="scanner-guide"' in html
    assert html.count('class="scanner-help"') == 1


def test_arch_004_scan_page_loads_scripts_from_our_server(client):
    html = client.get("/scan").text
    sources = re.findall(r'(?:src|data-wasm)="([^"]+)"', html)
    assert set(SCANNER_FILES) <= set(sources)
    assert all(s.startswith("/static/") for s in sources)


@pytest.mark.parametrize("path", SCANNER_FILES)
def test_arch_004_scanner_files_are_served(client, path):
    assert client.get(path).status_code == 200


def test_arch_004_wasm_served_as_wasm(client):
    # Browsers only stream-compile a .wasm file sent with this type.
    response = client.get(f"{VENDOR}/zxing-wasm-3.1.3-reader.wasm")
    assert response.headers["content-type"] == "application/wasm"


FAKE_KEY = "test-only-fake-signing-key"  # never a real key (SAFE-030)
FAKE_NOW = 1_800_000_000.0  # fixed clock, not a game number


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setenv(qr.KEY_ENV, FAKE_KEY)
    app = create_app()
    app.state.db_path = tmp_path / "scan.db"
    # Typed answers below. The verse question has pickers and its own tests (WRAP-012).
    categories = app.state.config["icebreaker"]["categories"]
    categories[:] = [c for c in categories if c != "verse"]
    ids = seed_fake_players(
        app.state.db_path, FAKE_PLAYER.public_id, "testpid02", "testpid03"
    )
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    app.dependency_overrides[scan.current_time] = lambda: FAKE_NOW
    c = TestClient(app, base_url="https://testserver")
    c.get("/scan")  # sets the CSRF cookie
    return c, ids


def _post_scan(c, public_id, token=True, now=FAKE_NOW):
    data = {"payload": qr.payload(qr.PLAYER_KIND, public_id, now, load_config()["qr"])}
    if token:
        data["csrf_token"] = c.cookies.get(csrf.COOKIE)
    return c.post("/scan", data=data, headers={"HX-Request": "true"})


def _as(c, public_id):
    c.app.dependency_overrides[get_current_player] = lambda: CurrentPlayer(public_id, 0)


def test_arch_038_scan_needs_csrf_token(db):
    c, _ = db
    response = _post_scan(c, "testpid02", token=False)
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text


def test_dec_061_scan_logged_out_goes_to_login():
    # A Scan page left open after logging out still has a good CSRF token.
    c = TestClient(create_app(), base_url="https://testserver")
    c.cookies.set(csrf.COOKIE, "test-only-token")
    response = c.post(
        "/scan",
        data={"csrf_token": "test-only-token", "payload": ""},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/login"


def test_game_017_scan_opens_the_icebreaker(db):
    c, _ = db
    response = _post_scan(c, "testpid02")
    assert response.status_code == 204
    assert re.fullmatch(r"/connections/\d+", response.headers["hx-redirect"])
    page = c.get(response.headers["hx-redirect"]).text
    assert "Test · Example Church A" in page


def test_safe_004_icebreaker_never_shows_last_name(db):
    c, _ = db
    assert (
        "Player 2" not in c.get(_post_scan(c, "testpid02").headers["hx-redirect"]).text
    )


@pytest.mark.parametrize(
    ("scanned", "status", "code"),
    [
        (FAKE_PLAYER.public_id, 400, "BAD_INPUT"),  # GAME-014
        ("testpid99", 404, "NOT_FOUND"),
    ],
)
def test_api_005_refused_scan_shows_error_partial(db, scanned, status, code):
    c, _ = db
    response = _post_scan(c, scanned)
    assert response.status_code == status
    assert f'data-error-code="{code}"' in response.text


def test_game_013_scanning_again_says_already_connected(db):
    c, _ = db
    _post_scan(c, "testpid02")
    _as(c, "testpid02")
    response = _post_scan(c, FAKE_PLAYER.public_id)
    assert response.status_code == 409
    assert "You two are already connected!" in response.text


def test_arch_022_old_code_says_expired(db):
    c, _ = db
    old = FAKE_NOW - 10 * load_config()["qr"]["rotation_seconds"]
    response = _post_scan(c, "testpid02", now=old)
    assert response.status_code == 410
    assert 'data-error-code="CODE_EXPIRED"' in response.text


@pytest.mark.parametrize(("state", "code"), [("paused", "PAUSED"), ("off", "GAME_OFF")])
def test_api_020_scan_while_game_not_on_is_423(db, state, code):
    c, _ = db
    conn = connect(c.app.state.db_path)
    set_state(conn, state)
    conn.close()
    response = _post_scan(c, "testpid02")
    assert response.status_code == 423
    assert f'data-error-code="{code}"' in response.text


def _connection_id(response):
    return int(response.headers["hx-redirect"].rsplit("/", 1)[1])


def _question(html):
    return re.search(r"<h1>(.+?)</h1>", html).group(1)


def test_game_017_icebreaker_shows_the_pairs_question_to_both(db):
    c, _ = db
    path = f"/connections/{_connection_id(_post_scan(c, 'testpid02'))}"
    question = _question(c.get(path).text)
    _as(c, "testpid02")
    assert _question(c.get(path).text) == question


def test_safe_006_icebreaker_hidden_from_everyone_else(db):
    c, _ = db
    path = f"/connections/{_connection_id(_post_scan(c, 'testpid02'))}"
    _as(c, "testpid03")
    response = c.get(path)
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text
    assert c.get("/connections/999").text == response.text


def _post_answer(c, connection_id, answer="Example answer", token=True, htmx=True):
    data = {"answer": answer}
    if token:
        data["csrf_token"] = c.cookies.get(csrf.COOKIE)
    headers = {"HX-Request": "true"} if htmx else {}
    return c.post(f"/connections/{connection_id}/answer", data=data, headers=headers)


def test_game_016_saving_an_answer_shows_the_points_earned(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    response = _post_answer(c, met_id)
    assert response.status_code == 200
    assert "<html" not in response.text  # API-002: only the answer card
    points = load_config()["points"]["connect_same_church"]  # AI-013
    assert f"Saved! You earned {points} points." in response.text
    assert "Example answer" in response.text
    assert "<form" not in response.text


def test_game_015_icebreaker_shows_your_saved_answer_instead_of_the_form(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    form = c.get(f"/connections/{met_id}").text
    assert f'hx-post="/connections/{met_id}/answer"' in form
    assert "Test's answer" in form
    _post_answer(c, met_id)
    page = c.get(f"/connections/{met_id}").text
    assert "Example answer" in page
    assert 'name="answer"' not in page


def test_safe_006_other_player_never_sees_your_answer(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    _post_answer(c, met_id, answer="Example answer zq9")
    _as(c, "testpid02")
    page = c.get(f"/connections/{met_id}").text
    assert "Example answer zq9" not in page
    assert 'name="answer"' in page  # they still type their own


def test_safe_006_someone_outside_the_pair_cannot_save(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    _as(c, "testpid03")
    response = _post_answer(c, met_id)
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text
    assert "<form" not in response.text


def test_arch_038_answer_needs_csrf_token(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    response = _post_answer(c, met_id, token=False)
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text


def test_game_016_saving_twice_says_already_done(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    _post_answer(c, met_id)
    response = _post_answer(c, met_id, answer="Another answer")
    assert response.status_code == 409
    assert 'data-error-code="ALREADY_DONE"' in response.text
    assert "Example answer" in response.text  # the first answer stays


def test_api_005_blank_answer_keeps_the_form(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    response = _post_answer(c, met_id, answer="   ")
    assert response.status_code == 400
    assert "Type their answer first." in response.text
    assert 'name="answer"' in response.text


@pytest.mark.parametrize(("state", "code"), [("paused", "PAUSED"), ("off", "GAME_OFF")])
def test_api_020_answer_while_game_not_on_is_423(db, state, code):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    conn = connect(c.app.state.db_path)
    set_state(conn, state)
    conn.close()
    response = _post_answer(c, met_id)
    assert response.status_code == 423
    assert f'data-error-code="{code}"' in response.text
    assert (
        'value="Example answer"' in response.text
    )  # kept for when the game is back on


def test_api_007_answer_works_without_javascript(db):
    c, _ = db
    met_id = _connection_id(_post_scan(c, "testpid02"))
    response = _post_answer(c, met_id, htmx=False)
    assert response.status_code == 200
    assert "<html" in response.text
    assert "Saved! You earned" in response.text


def _poll(c):
    return re.search(r'hx-get="(/code/incoming[^"]+)"', c.get("/code").text).group(1)


def test_api_032_incoming_opens_the_icebreaker_once_someone_scans(db):
    c, _ = db
    _as(c, "testpid02")
    poll = _poll(c)
    nothing = c.get(poll)
    assert nothing.status_code == 204
    assert "hx-redirect" not in nothing.headers
    _as(c, FAKE_PLAYER.public_id)
    met = _post_scan(c, "testpid02")  # Test Player 1 scans Test Player 2
    _as(c, "testpid02")
    response = c.get(poll)
    assert response.headers["hx-redirect"] == met.headers["hx-redirect"]
    assert response.headers["cache-control"] == "no-store"


def test_api_032_incoming_opens_the_first_of_several_scans(db):
    c, _ = db
    _as(c, "testpid02")
    poll = _poll(c)
    _as(c, FAKE_PLAYER.public_id)
    first = _post_scan(c, "testpid02")
    _as(c, "testpid03")
    _post_scan(c, "testpid02")
    _as(c, "testpid02")
    assert c.get(poll).headers["hx-redirect"] == first.headers["hx-redirect"]


def test_api_032_incoming_ignores_scans_you_made(db):
    c, _ = db
    poll = _poll(c)
    _post_scan(c, "testpid02")
    assert "hx-redirect" not in c.get(poll).headers


def test_api_030_incoming_polls_at_config_interval(db):
    c, _ = db
    seconds = load_config()["qr"]["incoming_poll_seconds"]
    assert f'hx-trigger="every {seconds}s"' in c.get("/code").text


def test_dec_061_incoming_logged_out_goes_to_login():
    response = TestClient(create_app()).get(
        "/code/incoming", headers={"HX-Request": "true"}
    )
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/login"


def _verse_pair(c):
    c.app.state.config["icebreaker"]["categories"][:] = ["verse"]
    return _connection_id(_post_scan(c, "testpid02"))


def _post_verse(c, connection_id, book, chapter, verse):
    data = {"book": book, "chapter": chapter, "verse": verse}
    data["csrf_token"] = c.cookies.get(csrf.COOKIE)
    headers = {"HX-Request": "true"}
    return c.post(f"/connections/{connection_id}/answer", data=data, headers=headers)


def test_wrap_012_verse_question_shows_pickers_not_a_text_box(db):
    c, _ = db
    page = c.get(f"/connections/{_verse_pair(c)}").text
    for name in ("book", "chapter", "verse"):
        assert f'<select id="{name}" name="{name}"' in page
    assert 'name="answer"' not in page
    assert 'id="bible-verses"' in page and "verse-picker.js" in page


def test_wrap_012_picked_verse_is_saved_as_book_chapter_verse(db):
    c, _ = db
    met_id = _verse_pair(c)
    response = _post_verse(c, met_id, "Song of Songs", "2", "4")
    assert response.status_code == 200
    assert "Song of Songs 2:4" in response.text
    assert "Song of Songs 2:4" in c.get(f"/connections/{met_id}").text


def test_wrap_012_chapter_too_high_is_refused_and_keeps_the_pickers(db):
    c, _ = db
    response = _post_verse(c, _verse_pair(c), "John", "22", "1")  # John has 21
    assert response.status_code == 400
    assert "Pick a book, chapter, and verse from the lists." in response.text
    assert 'name="book"' in response.text
