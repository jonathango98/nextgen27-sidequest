import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session, signup, staff_session
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")
STAFF_PAGES = ("/usher", "/admin")
FAKE_START = 1_800_000_000  # fixed clock, not a game number


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "staff-roles.db"


@pytest.fixture
def clock(monkeypatch):
    now = [FAKE_START]
    monkeypatch.setattr(staff_session, "_now", lambda: now[0])
    return now


@pytest.fixture
def client(monkeypatch, db_path, clock):
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


def _log_in(client, username, password):
    response = client.post(
        "/staff/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
    )
    assert response.status_code == 303
    return response


def _sent_to_login(response):
    return (response.status_code, response.headers.get("location")) == (
        303,
        "/staff/login",
    )


@pytest.mark.parametrize("path", STAFF_PAGES)
def test_arch_035_logged_out_staff_page_sends_to_login(client, path):
    assert _sent_to_login(client.get(path))


@pytest.mark.parametrize("path", STAFF_PAGES)
def test_arch_035_logged_out_htmx_request_redirects_by_header(client, path):
    response = client.get(path, headers={"HX-Request": "true"})
    assert (response.status_code, response.headers["HX-Redirect"]) == (
        204,
        "/staff/login",
    )


def test_arch_035_usher_cannot_open_admin_console(client):
    _log_in(client, *USHER)
    response = client.get("/admin")
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text
    assert "This page is for admins only." in response.text


def test_dec_063_admin_can_open_usher_console(client):
    _log_in(client, *ADMIN)
    response = client.get("/usher")
    assert response.status_code == 200
    assert 'href="/admin"' in response.text


@pytest.mark.parametrize("path", STAFF_PAGES)
def test_arch_035_player_session_is_not_staff(client, db_path, fake_pin, path):
    conn = connect(db_path)
    church = conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church A')"
    ).lastrowid
    public_id = signup.create_player(
        conn,
        signup.Details("Test", "Player 1", church, False),
        fake_pin,
        client.app.state.config,
    )
    conn.close()
    client.cookies.set(
        session.COOKIE, f"{public_id}.{session.sign('session', public_id)}"
    )
    assert _sent_to_login(client.get(path))


@pytest.mark.parametrize("path", STAFF_PAGES)
def test_arch_035_tampered_staff_cookie_refused(client, path):
    _log_in(client, *ADMIN)
    staff_id, issued, mac = client.cookies[staff_session.COOKIE].split(".")
    # Another account's id with the old signature. Delete first, so only the fake is sent.
    client.cookies.delete(staff_session.COOKIE)
    client.cookies.set(staff_session.COOKIE, f"{int(staff_id) + 1}.{issued}.{mac}")
    assert _sent_to_login(client.get(path))


def test_arch_035_player_cookie_value_is_not_a_staff_cookie(client):
    # The same key signs both, but for a different purpose, so values never swap.
    body = f"1.{FAKE_START}"
    client.cookies.set(staff_session.COOKIE, f"{body}.{session.sign('session', body)}")
    assert _sent_to_login(client.get("/admin"))


def test_dec_063_staff_login_ends_after_the_configured_hours(client, clock, hours):
    _log_in(client, *ADMIN)
    clock[0] = FAKE_START + hours * 60 * 60 - 1
    assert client.get("/admin").status_code == 200
    clock[0] = FAKE_START + hours * 60 * 60
    assert _sent_to_login(client.get("/admin"))


def test_arch_036_switched_off_account_is_logged_out_on_next_page(client, db_path):
    _log_in(client, *USHER)
    assert client.get("/usher").status_code == 200
    conn = connect(db_path)
    conn.execute(
        "UPDATE staff_account SET is_active = 0 WHERE username = ?", (USHER[0],)
    )
    conn.close()
    assert _sent_to_login(client.get("/usher"))


def test_dec_063_logout_ends_the_staff_session(client):
    _log_in(client, *ADMIN)
    response = client.post("/logout", data={"csrf_token": client.cookies[csrf.COOKIE]})
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/staff/login",
    )
    assert f'{staff_session.COOKIE}=""' in response.headers["set-cookie"]
    client.cookies.delete(staff_session.COOKIE)
    assert _sent_to_login(client.get("/admin"))
