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


def test_game_014_scan_shows_who_you_met_and_their_question(db):
    c, _ = db
    response = _post_scan(c, "testpid02")
    assert response.status_code == 200
    assert "<html" not in response.text  # API-002: only the fragment
    assert "You met Test!" in response.text
    assert "Example Church A" in response.text
    assert re.search(r'href="/connections/\d+">Open icebreaker</a>', response.text)


def test_safe_004_scan_result_never_shows_last_name(db):
    c, _ = db
    assert "Player 2" not in _post_scan(c, "testpid02").text


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
    return int(re.search(r'data-connection="(\d+)"', response.text).group(1))


def test_game_017_icebreaker_shows_the_pairs_question_to_both(db):
    c, _ = db
    met = _post_scan(c, "testpid02")
    question = re.search(r"<h2>(.+?)</h2>", met.text).group(1)
    path = f"/connections/{_connection_id(met)}"
    assert f"<h1>{question}</h1>" in c.get(path).text
    _as(c, "testpid02")
    assert f"<h1>{question}</h1>" in c.get(path).text


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


def test_api_032_incoming_is_204_until_someone_scans(db):
    c, _ = db
    _as(c, "testpid02")
    html = c.get("/code").text
    poll = (
        re.search(r'hx-get="(/code/incoming[^"]+)"', html)
        .group(1)
        .replace("&amp;", "&")
    )
    assert c.get(poll).status_code == 204
    _as(c, FAKE_PLAYER.public_id)
    _post_scan(c, "testpid02")  # Test Player 1 scans Test Player 2
    _as(c, "testpid02")
    response = c.get(poll)
    assert response.status_code == 200
    assert "Test just scanned you!" in response.text
    assert response.headers["cache-control"] == "no-store"
    # The next check asks only for newer scans, so the note stays put.
    newer = re.search(r'hx-get="(/code/incoming[^"]+)"', response.text).group(1)
    assert c.get(newer.replace("&amp;", "&")).status_code == 204


def test_api_032_incoming_ignores_scans_you_made(db):
    c, _ = db
    html = c.get("/code").text
    poll = (
        re.search(r'hx-get="(/code/incoming[^"]+)"', html)
        .group(1)
        .replace("&amp;", "&")
    )
    _post_scan(c, "testpid02")
    assert c.get(poll).status_code == 204


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
