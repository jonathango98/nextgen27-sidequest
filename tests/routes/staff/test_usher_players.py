import logging
from dataclasses import fields

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session, staff_session
from app.db import connect
from app.main import create_app
from app.services import players, qr
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
FAKE_PIN_HASH = "not-a-real-hash"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")
CHURCH = "Example Church A"
PAGE = "/usher/players"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "usher-players.db"


@pytest.fixture
def client(monkeypatch, db_path):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    with TestClient(
        create_app(), base_url="https://testserver", follow_redirects=False
    ) as c:
        conn = connect(db_path)
        create_account(conn, *ADMIN, "admin")
        create_account(conn, *USHER, "usher")
        conn.execute("INSERT INTO church (name) VALUES (?)", (CHURCH,))
        conn.close()
        c.get("/staff/login")  # sets the CSRF cookie
        yield c


def _log_in(client, account=USHER):
    username, password = account
    response = client.post(
        "/staff/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
    )
    assert response.status_code == 303


def _player(db_path, first="Test", last="Player", public_id="testpid01", minor=False):
    conn = connect(db_path)
    conn.execute(
        "INSERT INTO player"
        " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
        " VALUES (?, ?, ?, (SELECT id FROM church WHERE name = ?), ?, ?)",
        (public_id, first, last, CHURCH, int(minor), FAKE_PIN_HASH),
    )
    conn.close()
    return public_id


def _search(client, q):
    return client.get(PAGE, params={"q": q})


def _pick_link(public_id):
    return f'href="/usher/players?player={public_id}"'


@pytest.mark.parametrize(
    "q", ["Sam", "sam", "Kimball", "kim", "Sam Kim", "  sam   kimball "]
)
def test_game_113_search_finds_by_first_last_or_full_name(client, db_path, q):
    public_id = _player(db_path, "Sam", "Kimball")
    _log_in(client)
    assert _pick_link(public_id) in _search(client, q).text


def test_game_113_search_leaves_out_other_players(client, db_path):
    _player(db_path, "Sam", "Kimball", public_id="testpid01")
    other = _player(db_path, "Alex", "Rivers", public_id="testpid02")
    _log_in(client)
    assert _pick_link(other) not in _search(client, "Sam").text


def test_game_113_no_match_says_so(client, db_path):
    _player(db_path)
    _log_in(client)
    assert "No players found." in _search(client, "Nobody").text


@pytest.mark.parametrize("q", ["", "   "])
def test_game_113_empty_search_lists_nobody(client, db_path, q):
    public_id = _player(db_path)
    _log_in(client)
    html = _search(client, q).text
    assert _pick_link(public_id) not in html
    assert "No players found." not in html


@pytest.mark.parametrize("q", ["%", "_", "S_m", "\\"])
def test_game_113_wildcards_are_plain_text(client, db_path, q):
    public_id = _player(db_path, "Sam", "Kimball")
    _log_in(client)
    assert _pick_link(public_id) not in _search(client, q).text


def test_game_113_results_are_capped_and_say_there_are_more(client, db_path):
    for number in range(players.RESULTS_MAX + 1):
        _player(db_path, "Sam", f"Player {number}", public_id=f"testpid{number:02}")
    _log_in(client)
    html = _search(client, "Sam").text
    assert html.count('href="/usher/players?player=') == players.RESULTS_MAX
    assert "Type more of the name" in html


def test_game_113_exactly_the_cap_does_not_say_there_are_more(client, db_path):
    for number in range(players.RESULTS_MAX):
        _player(db_path, "Sam", f"Player {number}", public_id=f"testpid{number:02}")
    _log_in(client)
    assert "Type more of the name" not in _search(client, "Sam").text


def test_game_113_picking_a_player_shows_their_card(client, db_path):
    public_id = _player(db_path, "Sam", "Kimball")
    _log_in(client)
    html = client.get(PAGE, params={"player": public_id}).text
    assert "data-player-card" in html
    assert "Sam K." in html
    assert CHURCH in html


def test_api_005_picking_an_unknown_player_is_not_found(client):
    _log_in(client)
    response = client.get(PAGE, params={"player": "nobody00000x"})
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text


def test_safe_004_full_last_name_never_shown(client, db_path):
    public_id = _player(db_path, "Sam", "Kimball")
    _log_in(client)
    for html in (
        _search(client, "Kimball").text.replace('value="Kimball"', ""),
        client.get(PAGE, params={"player": public_id}).text,
    ):
        assert "Kimball" not in html
        assert "Sam K." in html


def test_safe_028_usher_lookup_reads_only_fields_an_usher_may_see():
    assert {field.name for field in fields(players.PlayerForUsher)} == {
        "public_id",
        "first_name",
        "last_initial",
        "church",
    }


def test_safe_028_usher_lookup_hides_under_18_and_pin(client, db_path):
    minor = _player(db_path, "Sam", "Kimball", public_id="testpid01", minor=True)
    adult = _player(db_path, "Sam", "Kimberly", public_id="testpid02")
    _log_in(client)
    # A minor's search result and card look the same as an adult's (SAFE-019).
    found = _search(client, "Sam").text
    assert found.count("Sam K. · Example Church A") == 2
    minor_card = client.get(PAGE, params={"player": minor}).text
    adult_card = client.get(PAGE, params={"player": adult}).text
    assert minor_card == adult_card
    assert FAKE_PIN_HASH not in found + minor_card


def test_game_112_finding_a_player_saves_nothing(client, db_path):
    public_id = _player(db_path)
    _log_in(client)
    _search(client, "Test")
    client.get(PAGE, params={"player": public_id})
    conn = connect(db_path)
    for table in ("point_ledger", "audit_log"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    conn.close()


def test_dec_063_admins_can_find_players_too(client, db_path):
    public_id = _player(db_path)
    _log_in(client, ADMIN)
    assert _pick_link(public_id) in _search(client, "Test").text


def test_arch_035_logged_out_goes_to_staff_login(client):
    response = _search(client, "Test")
    assert (response.status_code, response.headers["location"]) == (303, "/staff/login")


def test_arch_035_player_session_is_refused(client, db_path):
    public_id = _player(db_path)
    client.cookies.set(
        session.COOKIE, f"{public_id}.{session.sign('session', public_id)}"
    )
    response = _search(client, "Test")
    assert (response.status_code, response.headers["location"]) == (303, "/staff/login")
    assert staff_session.COOKIE not in client.cookies


def test_arch_001_names_are_escaped(client, db_path):
    _player(db_path, "<script>x</script>", "Player")
    _log_in(client)
    html = _search(client, "<script>").text
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x" in html


def test_safe_028_pages_with_names_are_never_cached(client, db_path):
    public_id = _player(db_path)
    _log_in(client)
    for response in (
        _search(client, "Test"),
        client.get(PAGE, params={"player": public_id}),
    ):
        assert response.headers["cache-control"] == "no-store"


def test_game_112_console_links_to_find_player(client):
    _log_in(client)
    assert f'href="{PAGE}"' in client.get("/usher").text


def test_arch_051_access_log_drops_the_query(client, caplog):
    # Starting the app turned the filter on. The format and arguments are uvicorn's own.
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logging.getLogger("uvicorn.access").info(
            '%s - "%s %s HTTP/%s" %d',
            "127.0.0.1:50000",
            "GET",
            f"{PAGE}?q=Kimball",
            "1.1",
            200,
        )
    message = caplog.records[-1].getMessage()
    assert "Kimball" not in message
    assert f"GET {PAGE} HTTP/1.1" in message
