import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session, staff_session
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "staff-login.db"


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
        conn.close()
        c.get("/staff/login")  # sets the CSRF cookie
        yield c


@pytest.fixture
def hours(client):
    return client.app.state.config["auth"]["staff_session_hours"]


def _log_in(client, username, password, **headers):
    return client.post(
        "/staff/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
        headers=headers,
    )


def _error_code(response):
    return re.search(r'data-error-code="([A-Z_]+)"', response.text).group(1)


def _switch_off(db_path, username):
    conn = connect(db_path)
    conn.execute(
        "UPDATE staff_account SET is_active = 0 WHERE username = ?", (username,)
    )
    conn.close()


def test_arch_036_staff_login_page_asks_for_username_and_password(client):
    page = client.get("/staff/login")
    assert page.status_code == 200
    assert 'name="username"' in page.text
    assert 'name="password" type="password"' in page.text
    assert 'name="csrf_token"' in page.text


def test_arch_035_admin_lands_on_admin_console(client):
    response = _log_in(client, *ADMIN)
    assert (response.status_code, response.headers["location"]) == (303, "/admin")
    console = client.get("/admin")
    assert console.status_code == 200
    assert "test-admin-1" in console.text


def test_arch_035_usher_lands_on_usher_console(client):
    response = _log_in(client, *USHER)
    assert (response.status_code, response.headers["location"]) == (303, "/usher")
    assert client.get("/usher").status_code == 200


def test_arch_036_username_ignores_case_and_spaces(client):
    response = _log_in(client, "  TEST-ADMIN-1 ", ADMIN[1])
    assert response.headers["location"] == "/admin"


def test_arch_036_htmx_login_redirects_with_a_header(client):
    response = _log_in(client, *USHER, **{"HX-Request": "true"})
    assert (response.status_code, response.headers["HX-Redirect"]) == (204, "/usher")


@pytest.mark.parametrize(
    ("username", "password"),
    [(ADMIN[0], "wrong password"), ("test-nobody", ADMIN[1])],
)
def test_arch_036_wrong_password_and_unknown_user_look_the_same(
    client, username, password
):
    response = _log_in(client, username, password)
    assert response.status_code == 400
    assert _error_code(response) == "BAD_INPUT"
    assert "log you in with that username and password" in response.text
    assert staff_session.COOKIE not in response.cookies


def test_arch_036_password_is_never_sent_back(client):
    response = _log_in(client, ADMIN[0], "wrong password")
    assert "wrong password" not in response.text
    assert 'value="test-admin-1"' in response.text


@pytest.mark.parametrize(
    ("username", "password"), [("", ADMIN[1]), (ADMIN[0], ""), ("   ", ADMIN[1])]
)
def test_arch_036_missing_fields_refused(client, username, password):
    response = _log_in(client, username, password)
    assert response.status_code == 400
    assert "Please fill in your username and password." in response.text


def test_arch_036_switched_off_account_cannot_log_in(client, db_path):
    _switch_off(db_path, USHER[0])
    response = _log_in(client, *USHER)
    assert response.status_code == 400
    assert "log you in with that username and password" in response.text


def test_arch_038_staff_login_needs_csrf(client):
    response = client.post(
        "/staff/login", data={"username": ADMIN[0], "password": ADMIN[1]}
    )
    assert response.status_code == 400
    assert staff_session.COOKIE not in response.cookies


def test_dec_061_cookie_lasts_the_configured_hours(client, hours):
    cookie = _log_in(client, *ADMIN).headers["set-cookie"]
    assert cookie.startswith(f"{staff_session.COOKIE}=")
    assert f"Max-Age={hours * 60 * 60}" in cookie
    for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
        assert flag in cookie


def test_arch_035_logged_in_staff_skips_the_login_page(client):
    _log_in(client, *USHER)
    response = client.get("/staff/login")
    assert (response.status_code, response.headers["location"]) == (303, "/usher")
