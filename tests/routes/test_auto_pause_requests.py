import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.auth.current import CurrentPlayer, get_current_player
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.game_state import BANNERS, current_state, set_state
from tests.conftest import seed_fake_players

FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=120)  # fake data (ENG-047)
FAKE_QR_KEY = "test-only-fake-signing-key"  # never a real key (SAFE-030)
PAST_START = "2026-01-01T15:30:00Z"  # already passed, made up (SAFE-031)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "side-quest.db"))
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    app = create_app()
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    with TestClient(app, base_url="https://testserver") as c:
        seed_fake_players(c.app.state.db_path, FAKE_PLAYER.public_id)
        yield c


def _db(client):
    return connect(client.app.state.db_path)


def _session_starting(client, starts_at):
    # As if an admin added it earlier and its start time has now come (GAME-107).
    conn = _db(client)
    try:
        conn.execute(
            "INSERT INTO session (public_id, title, starts_at, checkin_open_minutes)"
            " VALUES ('testsession1', 'Example Session 1', ?, 15)",
            (starts_at,),
        )
    finally:
        conn.close()


def _state(client):
    conn = _db(client)
    try:
        return current_state(conn)
    finally:
        conn.close()


def test_game_107_next_player_page_shows_the_paused_note(client):
    _session_starting(client, PAST_START)
    response = client.get("/")
    assert response.status_code == 200
    assert BANNERS["paused"] in response.text  # UI-033, ARCH-042: this very request
    assert _state(client) == "paused"


def test_game_107_off_game_stays_off_on_the_next_page(client):
    conn = _db(client)
    set_state(conn, "off")
    conn.close()
    _session_starting(client, PAST_START)
    client.get("/")
    assert _state(client) == "off"


def test_game_107_start_time_still_to_come_changes_nothing(client):
    _session_starting(client, "2099-01-01T00:00:00Z")
    client.get("/")
    assert _state(client) == "on"


def test_dec_029_health_and_files_never_touch_the_database(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        main_module.sessions, "apply_auto_pause", lambda *a: calls.append(a)
    )
    assert client.get("/health").text == "ok"
    assert client.get("/static/css/player.css").status_code == 200
    assert calls == []
    client.get("/")
    assert len(calls) == 1


def test_ops_001_a_failed_check_never_breaks_a_page(client, monkeypatch):
    def broken(*args):
        raise main_module.sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(main_module.sessions, "apply_auto_pause", broken)
    assert client.get("/").status_code == 200
