import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.game_state import current_state
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "game-state-controls.db"


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


def _press(client, state, **headers):
    return client.post(
        "/admin/game-state",
        data={"state": state, "csrf_token": client.cookies[csrf.COOKIE]},
        headers=headers,
    )


def _state(db_path):
    conn = connect(db_path)
    try:
        return current_state(conn)
    finally:
        conn.close()


def _audit_actions(db_path):
    conn = connect(db_path)
    try:
        return [r[0] for r in conn.execute("SELECT action FROM audit_log")]
    finally:
        conn.close()


def _button(html, label):
    return re.search(rf"<button[^>]*>{label}</button>", html).group(0)


def test_game_110_admin_console_shows_state_and_three_buttons(client):
    _log_in(client, *ADMIN)
    html = client.get("/admin").text
    assert 'data-state="on"' in html
    assert "disabled" in _button(html, "Start")
    for label in ("Pause", "Off"):
        assert "disabled" not in _button(html, label)


def test_game_101_htmx_pause_returns_only_the_panel(client, db_path):
    _log_in(client, *ADMIN)
    response = _press(client, "paused", **{"HX-Request": "true"})
    assert response.status_code == 200
    assert '<section id="game-state"' in response.text
    assert "<html" not in response.text  # API-002: a partial, not the whole page
    assert 'data-state="paused"' in response.text
    assert "disabled" in _button(response.text, "Pause")
    assert _state(db_path) == "paused"


def test_game_101_plain_press_goes_back_to_the_console(client, db_path):
    _log_in(client, *ADMIN)
    response = _press(client, "paused")
    assert (response.status_code, response.headers["location"]) == (303, "/admin")
    assert _state(db_path) == "paused"


def test_game_104_admin_starts_and_switches_off(client, db_path):
    _log_in(client, *ADMIN)
    _press(client, "off")
    assert _state(db_path) == "off"
    _press(client, "on")
    assert _state(db_path) == "on"


def test_arch_050_each_press_writes_one_audit_row(client, db_path):
    _log_in(client, *ADMIN)
    for state in ("paused", "paused", "on", "off"):
        _press(client, state)
    # The second Pause changed nothing, so it wrote nothing.
    assert _audit_actions(db_path) == ["pause", "game_on", "game_off"]


def test_game_108_off_asks_to_confirm_but_pause_does_not(client):
    _log_in(client, *ADMIN)
    forms = re.findall(r"<form [^>]*>", client.get("/admin").text)
    confirms = [f for f in forms if "hx-confirm" in f]
    assert len(confirms) == 1
    assert "Sign-up closes" in confirms[0]


def test_arch_035_usher_cannot_set_game_state(client, db_path):
    _log_in(client, *USHER)
    response = _press(client, "paused")
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text
    assert _state(db_path) == "on"
    assert _audit_actions(db_path) == []


def test_arch_035_logged_out_cannot_set_game_state(client, db_path):
    response = _press(client, "paused")
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/staff/login",
    )
    assert _state(db_path) == "on"


def test_arch_038_game_state_needs_csrf(client, db_path):
    _log_in(client, *ADMIN)
    response = client.post("/admin/game-state", data={"state": "paused"})
    assert response.status_code == 400
    assert _state(db_path) == "on"


@pytest.mark.parametrize("htmx", [False, True])
def test_api_005_unknown_state_is_refused(client, db_path, htmx):
    _log_in(client, *ADMIN)
    headers = {"HX-Request": "true"} if htmx else {}
    response = _press(client, "sleeping", **headers)
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text
    assert "Please pick Start, Pause, or Off." in response.text
    assert _state(db_path) == "on"
    assert _audit_actions(db_path) == []
