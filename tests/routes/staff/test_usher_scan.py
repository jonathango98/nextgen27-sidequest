import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.routes.staff import usher
from app.services import qr
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
FAKE_PIN_HASH = "not-a-real-hash"
FAKE_NOW = 1_800_000_000  # fixed clock, not a game number
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")
CHURCH = "Example Church A"
PUBLIC_ID = "testpid01"
SCAN = "/usher/scan"
QR = load_config()["qr"]


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "usher-scan.db"


@pytest.fixture
def client(monkeypatch, db_path):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    app = create_app()
    app.dependency_overrides[usher.current_time] = lambda: FAKE_NOW
    with TestClient(app, base_url="https://testserver", follow_redirects=False) as c:
        conn = connect(db_path)
        create_account(conn, *ADMIN, "admin")
        create_account(conn, *USHER, "usher")
        conn.execute("INSERT INTO church (name) VALUES (?)", (CHURCH,))
        conn.execute(
            "INSERT INTO player"
            " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " VALUES (?, 'Sam', 'Kimball', (SELECT id FROM church), 1, ?)",
            (PUBLIC_ID, FAKE_PIN_HASH),
        )
        conn.close()
        c.get("/staff/login")  # sets the CSRF cookie
        yield c


def _log_in(client, account=USHER):
    username, password = account
    response = client.post(
        "/staff/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
    )
    assert response.status_code == 303


def _scan(client, payload):
    return client.post(
        SCAN,
        data={"payload": payload, "csrf_token": client.cookies[csrf.COOKIE]},
        headers={"HX-Request": "true"},
    )


def _code(public_id=PUBLIC_ID, now=FAKE_NOW):
    return qr.payload(qr.PLAYER_KIND, public_id, now, QR)


def test_game_112_scan_shows_who_it_is(client):
    _log_in(client)
    response = _scan(client, _code())
    assert response.status_code == 200
    assert "data-player-card" in response.text
    assert "Sam K." in response.text
    assert CHURCH in response.text


def test_api_002_scan_answers_with_only_the_fragment(client):
    _log_in(client)
    assert "<html" not in _scan(client, _code()).text


def test_dec_065_scan_hides_the_full_last_name(client):
    _log_in(client)
    assert "Kimball" not in _scan(client, _code()).text


def test_safe_028_scan_hides_under_18_and_pin(client):
    # The fixture's player is under 18, and nothing on the card says so.
    _log_in(client)
    html = _scan(client, _code()).text
    assert FAKE_PIN_HASH not in html
    assert "18" not in html


def test_game_112_scan_saves_nothing(client, db_path):
    _log_in(client)
    _scan(client, _code())
    conn = connect(db_path)
    for table in ("point_ledger", "audit_log", "connection"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    conn.close()


def test_arch_022_code_from_the_window_before_is_accepted(client):
    _log_in(client)
    earlier = FAKE_NOW - QR["rotation_seconds"] * QR["accepted_previous_steps"]
    assert _scan(client, _code(now=earlier)).status_code == 200


def test_arch_022_older_code_is_expired(client):
    _log_in(client)
    steps = QR["accepted_previous_steps"] + 1
    response = _scan(client, _code(now=FAKE_NOW - QR["rotation_seconds"] * steps))
    assert response.status_code == 410
    assert 'data-error-code="CODE_EXPIRED"' in response.text
    assert "Sam" not in response.text


def test_arch_026_forged_code_is_refused(client):
    _log_in(client)
    real = _code()
    last_digit = (int(real[-1]) + 1) % 10
    response = _scan(client, f"{real[:-1]}{last_digit}")
    assert response.status_code == 410
    assert "Sam" not in response.text


def test_arch_026_a_code_for_someone_else_is_refused(client):
    _log_in(client)
    code = _code().rsplit(".", 1)[1]
    response = _scan(client, f"{QR['format_version']}.P.testpid02.{code}")
    assert response.status_code == 410


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "https://example.com/menu",
        f"{QR['format_version']}x.P.{PUBLIC_ID}.000000",
        f"{QR['format_version']}.S.{PUBLIC_ID}.000000",  # a session code, not My Code
        f"{QR['format_version']}.P..000000",
        f"{QR['format_version']}.P.{PUBLIC_ID}",
        f"{QR['format_version']}.P.{PUBLIC_ID}.000000.extra",
    ],
)
def test_arch_025_anything_else_is_not_a_code(client, payload):
    _log_in(client)
    response = _scan(client, payload)
    assert response.status_code == 400
    assert 'data-error-code="NOT_A_CODE"' in response.text


def test_api_005_real_code_for_a_player_who_is_gone_is_not_found(client):
    _log_in(client)
    response = _scan(client, _code(public_id="nobody00000x"))
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text


def test_arch_038_scan_without_the_csrf_token_is_refused(client):
    _log_in(client)
    response = client.post(SCAN, data={"payload": _code()})
    assert response.status_code == 400
    assert "Sam" not in response.text


def test_dec_063_admins_can_scan_too(client):
    _log_in(client, ADMIN)
    assert _scan(client, _code()).status_code == 200


def test_arch_035_logged_out_scan_goes_to_staff_login(client):
    response = _scan(client, _code())
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/staff/login"


def test_arch_035_player_session_cannot_scan(client):
    client.cookies.set(
        session.COOKIE, f"{PUBLIC_ID}.{session.sign('session', PUBLIC_ID)}"
    )
    response = _scan(client, _code())
    assert response.headers["hx-redirect"] == "/staff/login"
    assert "Sam" not in response.text


def test_safe_028_scan_answer_is_never_cached(client):
    _log_in(client)
    assert _scan(client, _code()).headers["cache-control"] == "no-store"


def test_game_112_usher_console_has_the_scanner(client):
    _log_in(client)
    html = client.get("/usher").text
    assert "data-scanner" in html
    assert f'hx-post="{SCAN}"' in html
    assert f'data-format="{QR["format_version"]}"' in html


def test_game_112_admin_console_has_no_scanner(client):
    _log_in(client, ADMIN)
    assert "data-scanner" not in client.get("/admin").text
