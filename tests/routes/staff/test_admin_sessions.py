import copy
import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.game_state import current_state, set_state
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")
FORM = {
    "title": "Example Session 1",
    "starts_at": "2027-03-06T09:30",
    "checkin_open_minutes": "15",
}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "admin-sessions.db"


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
    response = client.post(
        "/staff/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
    )
    assert response.status_code == 303


def _post(client, path, data=None, **headers):
    return client.post(
        path,
        data={**(data or {}), "csrf_token": client.cookies[csrf.COOKIE]},
        headers=headers,
    )


def _db(db_path, sql, params=()):
    conn = connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _sessions(db_path):
    return _db(db_path, "SELECT * FROM session ORDER BY id")


def _set(db_path, state):
    conn = connect(db_path)
    try:
        set_state(conn, state)
    finally:
        conn.close()


def _state(db_path):
    conn = connect(db_path)
    try:
        return current_state(conn)
    finally:
        conn.close()


def _added(client, db_path, form=FORM):
    assert _post(client, "/admin/sessions", form).status_code == 303
    return _sessions(db_path)[-1]


def test_game_110_admin_adds_a_session_and_sees_it_after_refresh(client, db_path):
    _log_in(client, *ADMIN)
    response = _post(client, "/admin/sessions", FORM)
    # Back to the list, so a refresh can't add it twice.
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/admin/sessions",
    )
    html = client.get("/admin/sessions").text
    assert "Example Session 1" in html
    # GAME-105: shown back in venue time, and the form is filled for editing.
    assert "Starts Sat Mar 6, 9:30 AM. Check-in opens 15 min before." in html
    assert 'value="2027-03-06T09:30"' in html
    assert len(_sessions(db_path)) == 1


def test_game_110_admin_edits_a_session_title(client, db_path):
    _log_in(client, *ADMIN)
    row = _added(client, db_path)
    response = _post(
        client,
        "/admin/sessions",
        {**FORM, "title": "Example Session 1b", "session": row["public_id"]},
    )
    assert response.status_code == 303
    rows = _sessions(db_path)
    assert [r["title"] for r in rows] == ["Example Session 1b"]
    assert "Example Session 1b" in client.get("/admin/sessions").text


@pytest.mark.parametrize(
    ("form", "message"),
    [
        ({"title": ""}, "Please give the session a title."),
        ({**FORM, "checkin_open_minutes": ""}, "how many minutes before the start"),
    ],
)
def test_api_005_bad_session_form_is_refused_and_keeps_what_was_typed(
    client, db_path, form, message
):
    _log_in(client, *ADMIN)
    response = _post(client, "/admin/sessions", form)
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text
    assert message in response.text
    if form["title"]:
        assert 'id="add-title" name="title" value="Example Session 1"' in response.text
    assert _sessions(db_path) == []


def test_api_005_editing_an_unknown_session_is_not_found(client, db_path):
    _log_in(client, *ADMIN)
    response = _post(client, "/admin/sessions", {**FORM, "session": "nosuchsession"})
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text
    assert _sessions(db_path) == []


def test_game_026_end_session_turns_a_paused_game_on(client, db_path):
    _log_in(client, *ADMIN)
    row = _added(client, db_path)
    _set(db_path, "paused")
    response = _post(client, f"/admin/sessions/{row['public_id']}/end")
    assert response.status_code == 200
    assert "Example Session 1 has ended. The game is on again" in response.text
    assert 'data-state="on"' in response.text
    assert _state(db_path) == "on"
    assert _sessions(db_path)[0]["ended_at"]


def test_game_026_end_session_twice_changes_nothing(client, db_path):
    _log_in(client, *ADMIN)
    row = _added(client, db_path)
    _set(db_path, "paused")
    path = f"/admin/sessions/{row['public_id']}/end"
    _post(client, path)
    _set(db_path, "paused")
    response = _post(client, path)
    assert response.status_code == 200
    assert "Example Session 1 had already ended. Nothing changed." in response.text
    assert _state(db_path) == "paused"
    actions = [r[0] for r in _db(db_path, "SELECT action FROM audit_log ORDER BY id")]
    assert actions == ["session_add", "session_end", "game_on"]


def test_game_026_end_session_while_off_says_the_game_is_still_off(client, db_path):
    _log_in(client, *ADMIN)
    row = _added(client, db_path)
    _set(db_path, "off")
    response = _post(client, f"/admin/sessions/{row['public_id']}/end")
    assert "The game is still off." in response.text
    assert _state(db_path) == "off"


def test_api_002_htmx_end_session_gets_the_page_with_the_list(client, db_path):
    _log_in(client, *ADMIN)
    row = _added(client, db_path)
    response = _post(
        client, f"/admin/sessions/{row['public_id']}/end", **{"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert '<section id="sessions"' in response.text  # hx-select picks this out


def test_game_026_end_session_asks_first(client, db_path):
    _log_in(client, *ADMIN)
    _added(client, db_path)
    forms = re.findall(r"<form [^>]*/end\"[^>]*>", client.get("/admin/sessions").text)
    assert len(forms) == 1
    assert "hx-confirm=" in forms[0]


def test_api_005_ending_an_unknown_session_is_not_found(client, db_path):
    _log_in(client, *ADMIN)
    _set(db_path, "paused")
    response = _post(client, "/admin/sessions/nosuchsession/end")
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text
    assert _state(db_path) == "paused"


def test_data_014_page_has_no_room_or_place_field(client):
    _log_in(client, *ADMIN)
    html = client.get("/admin/sessions").text
    names = set(re.findall(r'<input [^>]*name="([a-z_]+)"', html))
    assert names <= {
        "csrf_token",
        "session",
        "title",
        "starts_at",
        "checkin_open_minutes",
    }


def test_game_110_admin_console_links_to_sessions(client):
    _log_in(client, *ADMIN)
    assert 'href="/admin/sessions"' in client.get("/admin").text


def test_ops_001_sessions_page_says_auto_pause_is_only_a_backup(client, monkeypatch):
    _log_in(client, *ADMIN)
    assert "still press Pause" in client.get("/admin/sessions").text
    # A copy, so the cached config other tests read stays as it is.
    config = copy.deepcopy(client.app.state.config)
    config["game"]["auto_pause_schedule"] = False  # GAME-107 switched off
    monkeypatch.setattr(client.app.state, "config", config)
    assert "data-auto-pause" not in client.get("/admin/sessions").text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/admin/sessions"),
        ("post", "/admin/sessions"),
        ("post", "/admin/sessions/anything/end"),
    ],
)
def test_game_110_usher_is_refused(client, db_path, method, path):
    _log_in(client, *USHER)
    if method == "get":
        response = client.get(path)
    else:
        response = _post(client, path, FORM)
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text
    assert _sessions(db_path) == []


def test_arch_035_logged_out_goes_to_staff_login(client):
    response = client.get("/admin/sessions")
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/staff/login",
    )


def test_arch_038_session_forms_need_csrf(client, db_path):
    _log_in(client, *ADMIN)
    row = _added(client, db_path)
    _set(db_path, "paused")
    assert client.post("/admin/sessions", data=FORM).status_code == 400
    assert client.post(f"/admin/sessions/{row['public_id']}/end").status_code == 400
    assert len(_sessions(db_path)) == 1
    assert _state(db_path) == "paused"
