import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.churches import load
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "admin-churches.db"


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
        load(conn, ["Example Church A"])
        conn.close()
        c.get("/staff/login")  # sets the CSRF cookie
        yield c


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


def _post(client, data):
    return client.post(
        "/admin/churches",
        data={**data, "csrf_token": client.cookies[csrf.COOKIE]},
    )


def _db(db_path, sql, params=()):
    conn = connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _church_id(db_path, name):
    return _db(db_path, "SELECT id FROM church WHERE name = ?", (name,))[0]["id"]


def _names(db_path):
    return [r["name"] for r in _db(db_path, "SELECT name FROM church ORDER BY id")]


def test_safe_002_added_church_shows_in_the_sign_up_list(client, db_path):
    _log_in(client, *ADMIN)
    response = _post(client, {"name": "Example Church D"})
    # Back to the list, so a refresh can't add the church twice.
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/admin/churches",
    )
    assert "Example Church D" in client.get("/admin/churches").text
    assert "Example Church D" in client.get("/join").text


def test_safe_002_renamed_church_shows_its_new_name_at_sign_up(client, db_path):
    _log_in(client, *ADMIN)
    church_id = _church_id(db_path, "Example Church A")
    response = _post(client, {"church": str(church_id), "name": "Example Church E"})
    assert response.status_code == 303
    assert _church_id(db_path, "Example Church E") == church_id
    join = client.get("/join").text
    assert "Example Church E" in join
    assert "Example Church A" not in join


def test_arch_050_church_changes_write_audit_rows(client, db_path):
    _log_in(client, *ADMIN)
    _post(client, {"name": "Example Church D"})
    church_id = _church_id(db_path, "Example Church D")
    _post(client, {"church": str(church_id), "name": "Example Church E"})
    admin_id = _db(
        db_path, "SELECT id FROM staff_account WHERE username = ?", (ADMIN[0],)
    )[0]["id"]
    rows = _db(db_path, "SELECT * FROM audit_log ORDER BY id")
    assert [
        (r["actor_type"], r["actor_id"], r["action"], r["target_type"], r["target_id"])
        for r in rows
    ] == [
        ("admin", admin_id, "church_add", "church", church_id),
        ("admin", admin_id, "church_rename", "church", church_id),
    ]


def test_safe_002_refused_add_says_why_and_keeps_the_name(client, db_path):
    _log_in(client, *ADMIN)
    response = _post(client, {"name": "example church a"})
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text
    assert "already in the list" in response.text
    assert 'value="example church a"' in response.text
    assert _names(db_path) == ["Example Church A"]


def test_safe_002_refused_rename_keeps_the_rename_form_open(client, db_path):
    _log_in(client, *ADMIN)
    _post(client, {"name": "Example Church D"})
    church_id = _church_id(db_path, "Example Church D")
    response = _post(client, {"church": str(church_id), "name": " "})
    assert response.status_code == 400
    card = response.text[response.text.index(f'data-church="{church_id}"') :]
    assert (
        card[: card.index("</article>")].count('<details class="session-edit" open>')
        == 1
    )
    assert _names(db_path) == ["Example Church A", "Example Church D"]


@pytest.mark.parametrize("church", ["999", "abc"])
def test_safe_002_renaming_an_unknown_church_is_not_found(client, db_path, church):
    _log_in(client, *ADMIN)
    response = _post(client, {"church": church, "name": "Example Church E"})
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text
    assert _names(db_path) == ["Example Church A"]


@pytest.mark.parametrize("method", ["get", "post"])
def test_arch_035_usher_is_refused_on_the_churches_page(client, db_path, method):
    _log_in(client, *USHER)
    if method == "get":
        response = client.get("/admin/churches")
    else:
        response = _post(client, {"name": "Example Church D"})
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text
    assert _names(db_path) == ["Example Church A"]


def test_arch_035_logged_out_goes_to_staff_login(client):
    response = client.get("/admin/churches")
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/staff/login",
    )


def test_arch_038_church_form_needs_csrf(client, db_path):
    _log_in(client, *ADMIN)
    assert (
        client.post("/admin/churches", data={"name": "Example Church D"}).status_code
        == 400
    )
    assert _names(db_path) == ["Example Church A"]


def test_game_110_admin_console_links_to_churches(client):
    _log_in(client, *ADMIN)
    assert 'href="/admin/churches"' in client.get("/admin").text


def test_game_110_hidden_church_leaves_sign_up_and_comes_back(client, db_path):
    _log_in(client, *ADMIN)
    church_id = _church_id(db_path, "Example Church A")
    response = _post(client, {"action": "hide", "church": str(church_id)})
    assert response.status_code == 200
    assert "Example Church A is hidden from the sign-up list" in response.text
    assert ">Example Church A</option>" not in client.get("/join").text

    response = _post(client, {"action": "show", "church": str(church_id)})
    assert "Example Church A is back in the sign-up list." in response.text
    assert ">Example Church A</option>" in client.get("/join").text
    actions = [
        r["action"] for r in _db(db_path, "SELECT action FROM audit_log ORDER BY id")
    ]
    assert actions == ["church_hide", "church_show"]


def test_game_110_htmx_hide_swaps_only_the_church_list(client, db_path):
    _log_in(client, *ADMIN)
    church_id = _church_id(db_path, "Example Church A")
    response = client.post(
        "/admin/churches",
        data={
            "action": "hide",
            "church": str(church_id),
            "csrf_token": client.cookies[csrf.COOKIE],
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert 'id="churches"' in response.text
    assert "Hidden" in response.text


@pytest.mark.parametrize("church", ["999", "", "abc"])
def test_game_110_hiding_an_unknown_church_is_not_found(client, db_path, church):
    _log_in(client, *ADMIN)
    response = _post(client, {"action": "hide", "church": church})
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text


def test_arch_035_usher_cannot_hide_a_church(client, db_path):
    _log_in(client, *USHER)
    church_id = _church_id(db_path, "Example Church A")
    response = _post(client, {"action": "hide", "church": str(church_id)})
    assert response.status_code == 403
    assert _db(db_path, "SELECT is_hidden FROM church")[0]["is_hidden"] == 0
