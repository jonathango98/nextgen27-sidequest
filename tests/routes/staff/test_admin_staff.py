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
NEW_USHER = ("Test Usher", "test password only 3")
ADD = {
    "action": "add",
    "username": NEW_USHER[0],
    "password": NEW_USHER[1],
    "role": "usher",
}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "admin-staff.db"


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


def _log_in(client, username, password):
    return client.post(
        "/staff/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
    )


def _log_out(client):
    client.cookies.delete(staff_session.COOKIE)


def _post(client, data, **headers):
    return client.post(
        "/admin/staff",
        data={**data, "csrf_token": client.cookies[csrf.COOKIE]},
        headers=headers,
    )


def _db(db_path, sql, params=()):
    conn = connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _account(db_path, username):
    rows = _db(db_path, "SELECT * FROM staff_account WHERE username = ?", (username,))
    return rows[0] if rows else None


def _audit_actions(db_path):
    return [
        (r["actor_type"], r["action"], r["target_type"], r["target_id"])
        for r in _db(db_path, "SELECT * FROM audit_log ORDER BY id")
    ]


def _switch(client, db_path, username, action, **headers):
    account_id = _account(db_path, username)["id"]
    return _post(client, {"action": action, "account": str(account_id)}, **headers)


def test_arch_036_admin_adds_an_usher_who_can_log_in(client, db_path):
    assert _log_in(client, *ADMIN).status_code == 303
    response = _post(client, ADD)
    # Back to the list, so a refresh can't add the account twice.
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/admin/staff",
    )
    assert NEW_USHER[0] in client.get("/admin/staff").text
    _log_out(client)
    response = _log_in(client, *NEW_USHER)
    assert (response.status_code, response.headers["location"]) == (303, "/usher")


def test_arch_036_admin_adds_an_admin(client, db_path):
    _log_in(client, *ADMIN)
    _post(client, {**ADD, "username": "Test Admin 2", "role": "admin"})
    assert _account(db_path, "Test Admin 2")["role"] == "admin"


def test_arch_050_adding_an_account_writes_an_audit_row(client, db_path):
    _log_in(client, *ADMIN)
    _post(client, ADD)
    admin_id = _account(db_path, ADMIN[0])["id"]
    new_id = _account(db_path, NEW_USHER[0])["id"]
    rows = _db(db_path, "SELECT * FROM audit_log WHERE action = 'staff_add'")
    assert [(r["actor_id"], r["target_id"]) for r in rows] == [(admin_id, new_id)]


def test_ops_042_switched_off_usher_cannot_log_in_until_switched_on(client, db_path):
    _log_in(client, *ADMIN)
    _post(client, ADD)
    response = _switch(client, db_path, NEW_USHER[0], "switch_off")
    assert response.status_code == 200
    assert "Test Usher is switched off" in response.text
    assert _account(db_path, NEW_USHER[0])["is_active"] == 0
    _log_out(client)
    assert _log_in(client, *NEW_USHER).status_code != 303

    _log_in(client, *ADMIN)
    response = _switch(client, db_path, NEW_USHER[0], "switch_on")
    assert "Test Usher is switched on" in response.text
    _log_out(client)
    assert _log_in(client, *NEW_USHER).headers["location"] == "/usher"
    assert [a[1] for a in _audit_actions(db_path)] == [
        "staff_add",
        "staff_switch_off",
        "staff_switch_on",
    ]


def test_ops_042_htmx_switch_swaps_only_the_account_list(client, db_path):
    _log_in(client, *ADMIN)
    response = _switch(
        client, db_path, USHER[0], "switch_off", **{"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert 'id="accounts"' in response.text
    assert 'hx-select="#accounts"' in response.text


def test_arch_036_admin_cannot_switch_off_their_own_account(client, db_path):
    _log_in(client, *ADMIN)
    html = client.get("/admin/staff").text
    admin_id = _account(db_path, ADMIN[0])["id"]
    mine = html[html.index(f'data-account="{admin_id}"') :]
    mine = mine[: mine.index("</article>")]
    assert "Switch off" not in mine
    assert "This is you." in mine
    # The server checks too, not just the missing button (ARCH-035).
    response = _switch(client, db_path, ADMIN[0], "switch_off")
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text
    assert _account(db_path, ADMIN[0])["is_active"] == 1
    assert _audit_actions(db_path) == []


def test_arch_036_refused_add_keeps_the_username_but_never_the_password(
    client, db_path
):
    _log_in(client, *ADMIN)
    _post(client, ADD)
    response = _post(client, {**ADD, "username": "test usher"})
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text
    assert "There is already an account called test usher." in response.text
    assert 'value="test usher"' in response.text
    assert NEW_USHER[1] not in response.text
    assert len(_db(db_path, "SELECT * FROM staff_account")) == 3


@pytest.mark.parametrize(
    "form",
    [
        {**ADD, "username": " "},
        {**ADD, "password": ""},
        {**ADD, "role": "screen"},
        {"action": "delete", "account": "1"},
    ],
)
def test_arch_036_bad_staff_form_is_refused(client, db_path, form):
    _log_in(client, *ADMIN)
    response = _post(client, form)
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text
    assert len(_db(db_path, "SELECT * FROM staff_account")) == 2
    assert _audit_actions(db_path) == []


@pytest.mark.parametrize("account", ["999", "", "abc"])
def test_arch_036_switching_an_unknown_account_is_not_found(client, account):
    _log_in(client, *ADMIN)
    response = _post(client, {"action": "switch_off", "account": account})
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text


@pytest.mark.parametrize("method", ["get", "post"])
def test_arch_035_usher_is_refused_on_the_staff_page(client, db_path, method):
    _log_in(client, *USHER)
    if method == "get":
        response = client.get("/admin/staff")
    else:
        response = _post(client, ADD)
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text
    assert _account(db_path, NEW_USHER[0]) is None


def test_arch_035_logged_out_goes_to_staff_login(client):
    response = client.get("/admin/staff")
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/staff/login",
    )


def test_arch_038_staff_form_needs_csrf(client, db_path):
    _log_in(client, *ADMIN)
    assert client.post("/admin/staff", data=ADD).status_code == 400
    assert _account(db_path, NEW_USHER[0]) is None


def test_game_110_admin_console_links_to_staff(client):
    _log_in(client, *ADMIN)
    assert 'href="/admin/staff"' in client.get("/admin").text
