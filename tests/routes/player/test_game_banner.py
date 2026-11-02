import pytest
from fastapi.testclient import TestClient

from app.auth.current import CurrentPlayer, get_current_player
from app.db import connect
from app.main import create_app
from app.routes.player import join
from app.services import qr
from app.services.game_state import BANNERS, set_state

FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=120)  # fake data (ENG-047)
FAKE_QR_KEY = "test-only-fake-signing-key"  # never a real key (SAFE-030)
# Player pages with the bottom bar, which all share player/base.html (UI-030). Wrapped has its own
# full-screen frame and no note, since it is the main thing to do once the game is off (GAME-108).
PAGES = (
    "/",
    "/code",
    "/quests",
    "/scan",
    "/connections/1",
    "/journal",
    "/journal/new",
    "/summary",
    "/box",
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Own database per test, so a state change never leaks into other tests.
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "side-quest.db"))
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    app = create_app()
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    with TestClient(app, base_url="https://testserver") as c:
        yield c


def _set(client, state):
    conn = connect(client.app.state.db_path)
    try:
        set_state(conn, state)
    finally:
        conn.close()


def _banner(text):
    return f'<p class="game-banner" role="status">{text}</p>'


@pytest.mark.parametrize("path", PAGES)
def test_ui_033_paused_note_on_every_player_page(client, path):
    _set(client, "paused")
    response = client.get(path)
    assert response.status_code == 200
    assert _banner(BANNERS["paused"]) in response.text


@pytest.mark.parametrize("path", PAGES)
def test_game_108_closed_note_while_off(client, path):
    _set(client, "off")
    assert _banner(BANNERS["off"]) in client.get(path).text


@pytest.mark.parametrize("path", PAGES)
def test_ui_033_no_note_while_on(client, path):
    assert "game-banner" not in client.get(path).text


def test_arch_042_note_goes_away_on_the_next_page_after_start(client):
    _set(client, "paused")
    assert "game-banner" in client.get("/").text
    _set(client, "on")
    assert "game-banner" not in client.get("/").text


def test_game_108_join_page_says_closed_while_off(client):
    _set(client, "off")
    response = client.get("/join")
    assert response.status_code == 200
    assert join.CLOSED in response.text
    assert 'name="first_name"' not in response.text
    assert 'href="/login"' in response.text


def test_game_102_join_page_stays_open_while_paused(client):
    _set(client, "paused")
    response = client.get("/join")
    assert join.CLOSED not in response.text
    assert 'name="first_name"' in response.text


def test_game_108_login_page_still_works_while_off(client):
    _set(client, "off")
    response = client.get("/login")
    assert response.status_code == 200
    assert 'name="pin"' in response.text
