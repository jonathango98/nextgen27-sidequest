import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session, signup
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.services import qr

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
CHURCH = "Example Church A"


@pytest.fixture
def env(monkeypatch, tmp_path):
    db_path = tmp_path / "logout.db"
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    return db_path


@pytest.fixture
def church_id(env, fake_pin):
    with TestClient(create_app(), base_url="https://testserver"):
        conn = connect(env)
        church = conn.execute(
            "INSERT INTO church (name) VALUES (?)", (CHURCH,)
        ).lastrowid
        details = signup.Details("Test", "Player 1", church, False)
        signup.create_player(conn, details, fake_pin, load_config())
        conn.close()
    return church


@pytest.fixture
def phone(church_id, fake_pin):
    """A phone logged in as Test Player 1. Call it again for a second phone."""
    phones = []

    def log_in():
        client = TestClient(create_app(), base_url="https://testserver")
        client.__enter__()
        phones.append(client)
        client.get("/login")  # sets the CSRF cookie
        response = client.post(
            "/login",
            data={
                "csrf_token": client.cookies.get(csrf.COOKIE),
                "first_name": "Test",
                "last_name": "Player 1",
                "church_id": str(church_id),
                "pin": fake_pin,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        return client

    yield log_in
    for client in phones:
        client.__exit__(None, None, None)


def _logout(client, token=None, htmx=False):
    token = client.cookies.get(csrf.COOKIE) if token is None else token
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post(
        "/logout", data={"csrf_token": token}, headers=headers, follow_redirects=False
    )


def test_arch_034_logout_clears_cookie_and_goes_to_login(phone):
    client = phone()
    response = _logout(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{session.COOKIE}=")
    assert "Max-Age=0" in set_cookie
    assert "Path=/" in set_cookie and "Secure" in set_cookie
    assert session.COOKIE not in client.cookies


def test_api_002_htmx_logout_redirects_with_header(phone):
    client = phone()
    response = _logout(client, htmx=True)
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/login"
    assert session.COOKIE not in client.cookies


def test_arch_034_after_logout_player_pages_need_login(phone):
    client = phone()
    assert client.get("/").status_code == 200
    _logout(client)
    response = client.get("/")
    assert response.status_code == 401
    assert 'data-error-code="LOGIN_REQUIRED"' in response.text


def test_arch_034_logout_keeps_other_phone_logged_in(phone):
    first, second = phone(), phone()
    _logout(first)
    assert first.get("/code").status_code == 401
    assert second.get("/code").status_code == 200


def test_arch_038_logout_needs_csrf_token(phone):
    client = phone()
    response = _logout(client, token="not-the-token")
    assert response.status_code != 303
    assert session.COOKIE not in response.headers.get("set-cookie", "")
    assert client.get("/").status_code == 200


def test_arch_034_home_has_log_out_form(phone):
    client = phone()
    html = client.get("/").text
    form = html[html.index('action="/logout"') :]
    form = form[: form.index("</form>")]
    token = re.search(r'name="csrf_token" value="([^"]+)"', form).group(1)
    assert token == client.cookies.get(csrf.COOKIE)
    assert ">Log out</button>" in form
    assert 'hx-confirm="Log out on this phone?"' in form


def test_ui_036_log_out_is_in_settings_menu(phone):
    html = phone().get("/").text
    menu = html[html.index('<details class="menu">') : html.index("</details>")]
    assert 'aria-label="Settings"' in menu
    assert 'action="/logout"' in menu
    assert html.count('action="/logout"') == 1
