import pytest
from fastapi.testclient import TestClient

from app.auth import session
from app.main import create_app

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_PUBLIC_ID = "testpid01"


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "errors.db"))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    app = create_app()

    @app.get("/test-only-crash")  # not in the real app (API-001)
    def crash():
        raise RuntimeError("test-only secret detail")

    return app


@pytest.fixture
def client(app):
    with TestClient(
        app, base_url="https://testserver", raise_server_exceptions=False
    ) as c:
        yield c


def _log_in(client):
    value = f"{FAKE_PUBLIC_ID}.{session.sign('session', FAKE_PUBLIC_ID)}"
    client.cookies.set(session.COOKIE, value)


def test_api_021_unknown_page_is_a_friendly_not_found_page(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-error-code="NOT_FOUND"' in response.text
    assert "We couldn&#39;t find that." in response.text
    assert '<p class="brand">Side Quest</p>' in response.text


def test_dec_061_not_found_logged_out_offers_log_in(client):
    response = client.get("/no-such-page")
    assert 'href="/login"' in response.text
    assert "Back to Home" not in response.text


def test_dec_061_not_found_logged_in_offers_home(client):
    _log_in(client)
    response = client.get("/no-such-page")
    assert 'href="/">Back to Home' in response.text


def test_api_005_htmx_not_found_gets_the_partial(client):
    response = client.get("/no-such-page", headers={"HX-Request": "true"})
    assert response.status_code == 404
    assert "<html" not in response.text
    assert 'data-error-code="NOT_FOUND"' in response.text


def test_arch_037_screen_without_key_looks_like_any_not_found(client, monkeypatch):
    monkeypatch.delenv("SQ_SCREEN_KEY", raising=False)
    screen = client.get("/screen")
    unknown = client.get("/no-such-page")
    assert screen.status_code == 404
    assert screen.text == unknown.text


def test_api_005_other_http_errors_keep_the_default(client):
    response = client.post("/health")
    assert response.status_code == 405


def test_api_005_crash_shows_a_friendly_page_with_no_details(client):
    response = client.get("/test-only-crash")
    assert response.status_code == 500
    assert "Something went wrong" in response.text
    assert "test-only secret detail" not in response.text
    assert "RuntimeError" not in response.text
    assert 'href="/login"' in response.text
