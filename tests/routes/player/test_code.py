import pytest
from fastapi.testclient import TestClient

from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.main import create_app
from app.routes.player import code
from app.services import qr
from tests.routes.player.test_skeleton import current_tab

# Fake data (ENG-047), never a real key (SAFE-030).
FAKE_KEY = "test-only-fake-signing-key"
FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=120)
FAKE_NOW = 1_800_000_000.0  # fixed clock, not a game number
PATHS = ("/code", "/code/qr")


@pytest.fixture
def cfg():
    return load_config()["qr"]


@pytest.fixture
def window_start(cfg):
    rotation = cfg["rotation_seconds"]
    return FAKE_NOW // rotation * rotation


@pytest.fixture
def client(monkeypatch, window_start):
    monkeypatch.setenv(qr.KEY_ENV, FAKE_KEY)
    app = create_app()
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    app.dependency_overrides[code.current_time] = lambda: window_start
    return TestClient(app)


@pytest.mark.parametrize("path", PATHS)
def test_api_005_my_code_requires_login(path):
    response = TestClient(create_app()).get(path)
    assert response.status_code == 401
    assert 'data-error-code="LOGIN_REQUIRED"' in response.text


@pytest.mark.parametrize("path", PATHS)
def test_game_001_my_code_shows_current_payload(client, cfg, window_start, path):
    payload = qr.payload(qr.PLAYER_KIND, FAKE_PLAYER.public_id, window_start, cfg)
    response = client.get(path)
    assert response.status_code == 200
    assert code.qr_svg(payload) in response.text


@pytest.mark.parametrize("path", PATHS)
def test_game_001_my_code_is_never_cached(client, path):
    assert client.get(path).headers["cache-control"] == "no-store"


def test_ui_030_my_code_page_uses_player_frame(client):
    html = client.get("/code").text
    assert f'<span class="score">{FAKE_PLAYER.score}</span>' in html
    assert "/static/js/htmx.min.js" in html


def test_api_002_qr_partial_is_only_the_fragment(client):
    html = client.get("/code/qr").text
    assert "<html" not in html
    assert 'class="qr-panel"' in html


def test_api_030_refresh_waits_until_next_window(client, cfg, window_start):
    rotation = cfg["rotation_seconds"]
    client.app.dependency_overrides[code.current_time] = lambda: window_start + 0.5
    html = client.get("/code/qr").text
    assert f'hx-trigger="load delay:{rotation}s,' in html


def test_dec_031_failed_refresh_retries_after_config_wait(client, cfg):
    html = client.get("/code/qr").text
    assert f"[!detail.successful] delay:{cfg['poll_retry_seconds']}s" in html


@pytest.mark.parametrize("path", PATHS)
def test_arch_023_my_code_fails_closed_without_key(client, monkeypatch, cfg, path):
    monkeypatch.delenv(qr.KEY_ENV)
    response = TestClient(client.app, raise_server_exceptions=False).get(path)
    assert response.status_code == 500
    assert cfg["format_version"] not in response.text


def test_ui_037_my_code_has_scan_button(client):
    assert '<a class="button" href="/scan">Scan</a>' in client.get("/code").text


def test_ui_030_my_code_marks_its_tab(client):
    html = client.get("/code").text
    assert current_tab("/code", "My Code").search(html)
    assert html.count('aria-current="page"') == 1
