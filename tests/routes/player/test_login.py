import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session, signup
from app.db import connect
from app.main import create_app
from app.services import qr
from tests.conftest import make_fake_pin

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
CHURCHES = ("Example Church A", "Example Church B")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "login.db"


@pytest.fixture
def church_ids(db_path):
    return {}


@pytest.fixture
def client(monkeypatch, db_path, church_ids, fake_pin):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    with TestClient(create_app(), base_url="https://testserver") as c:
        conn = connect(db_path)
        for name in CHURCHES:
            church_ids[name] = conn.execute(
                "INSERT INTO church (name) VALUES (?)", (name,)
            ).lastrowid
        details = signup.Details("Test", "Player 1", church_ids[CHURCHES[0]], False)
        signup.create_player(conn, details, fake_pin)
        conn.close()
        c.get("/login")  # sets the CSRF cookie
        yield c


@pytest.fixture
def wrong_pin(cfg_auth):
    return make_fake_pin(cfg_auth["pin_digits"], start=5)


def _login(client, church_ids, pin, htmx=False, **overrides):
    data = {
        "csrf_token": client.cookies.get(csrf.COOKIE),
        "first_name": "Test",
        "last_name": "Player 1",
        "church_id": str(church_ids[CHURCHES[0]]),
        "pin": pin,
        **overrides,
    }
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post("/login", data=data, headers=headers, follow_redirects=False)


def _error_code(response):
    match = re.search(r'data-error-code="([A-Z_]+)"', response.text)
    return match and match.group(1)


def _alert(response):
    return re.search(r'role="alert"[^>]*>([^<]*)<', response.text).group(1)


def _player(db_path):
    conn = connect(db_path)
    row = conn.execute("SELECT * FROM player").fetchone()
    conn.close()
    return row


def test_arch_032_login_form_asks_full_name_church_and_pin(client):
    page = client.get("/login").text
    form = page[page.index("<form") : page.index("</form>")]
    names = set(re.findall(r'<(?:input|select)[^>]* name="([a-z_0-9]+)"', form))
    assert names == {"csrf_token", "first_name", "last_name", "church_id", "pin"}


def test_arch_032_login_with_full_name_church_and_pin(client, church_ids, fake_pin):
    response = _login(client, church_ids, fake_pin)
    assert response.status_code == 303
    assert response.headers["location"] == "/code"
    assert session.COOKIE in response.headers["set-cookie"]
    assert client.get("/code").status_code == 200


def test_arch_032_name_match_ignores_case_and_extra_spaces(
    client, church_ids, fake_pin
):
    response = _login(
        client, church_ids, fake_pin, first_name=" TEST ", last_name="player  1"
    )
    assert response.status_code == 303


def test_api_002_htmx_login_redirects_with_header(client, church_ids, fake_pin):
    response = _login(client, church_ids, fake_pin, htmx=True)
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/code"


def test_arch_032_wrong_pin_and_unknown_name_get_the_same_message(
    client, church_ids, wrong_pin, fake_pin
):
    wrong = _login(client, church_ids, wrong_pin, htmx=True)
    unknown = _login(client, church_ids, fake_pin, htmx=True, last_name="Player 9")
    other_church = _login(
        client,
        church_ids,
        fake_pin,
        htmx=True,
        church_id=str(church_ids[CHURCHES[1]]),
    )
    for response in (wrong, unknown, other_church):
        assert response.status_code == 400
        assert _error_code(response) == "BAD_INPUT"
    assert _alert(wrong) == _alert(unknown) == _alert(other_church)


@pytest.mark.parametrize("missing", ["first_name", "last_name", "church_id"])
def test_arch_032_every_field_is_required(client, church_ids, fake_pin, missing):
    response = _login(client, church_ids, fake_pin, htmx=True, **{missing: ""})
    assert response.status_code == 400
    assert _error_code(response) == "BAD_INPUT"


def test_safe_022_locks_after_max_wrong_tries(
    client, church_ids, wrong_pin, fake_pin, cfg_auth, db_path
):
    tries = cfg_auth["pin_max_attempts"]
    for _ in range(tries - 1):
        assert _login(client, church_ids, wrong_pin, htmx=True).status_code == 400
    locking = _login(client, church_ids, wrong_pin, htmx=True)
    assert locking.status_code == 403
    assert _error_code(locking) == "PIN_LOCKED"
    assert "find an admin at the game booth" in locking.text

    after = _login(client, church_ids, fake_pin, htmx=True)  # even the right PIN
    assert after.status_code == 403
    assert session.COOKIE not in after.headers.get("set-cookie", "")
    assert _player(db_path)["locked_at"] is not None


def test_safe_022_correct_pin_resets_the_count(
    client, church_ids, wrong_pin, fake_pin, cfg_auth, db_path
):
    tries = cfg_auth["pin_max_attempts"]
    for _ in range(tries - 1):
        _login(client, church_ids, wrong_pin, htmx=True)
    assert _login(client, church_ids, fake_pin, htmx=True).status_code == 204
    assert _player(db_path)["failed_pin_attempts"] == 0
    client.cookies.delete(session.COOKIE)
    for _ in range(tries - 1):
        assert _login(client, church_ids, wrong_pin, htmx=True).status_code == 400
    assert _player(db_path)["locked_at"] is None


def test_safe_022_no_tries_left_refuses_even_the_right_pin(
    client, church_ids, fake_pin, cfg_auth, db_path
):
    # Guesses sent at the same moment each take a try before the PIN is checked.
    conn = connect(db_path)
    conn.execute(
        "UPDATE player SET failed_pin_attempts = ?", (cfg_auth["pin_max_attempts"],)
    )
    conn.close()
    response = _login(client, church_ids, fake_pin, htmx=True)
    assert response.status_code == 403
    assert _error_code(response) == "PIN_LOCKED"


def test_safe_022_badly_formed_pin_does_not_use_a_try(
    client, church_ids, fake_pin, db_path
):
    response = _login(client, church_ids, fake_pin[:-1], htmx=True)
    assert response.status_code == 400
    assert _player(db_path)["failed_pin_attempts"] == 0


def test_arch_038_login_without_csrf_token_refused(client, church_ids, fake_pin):
    response = _login(client, church_ids, fake_pin, csrf_token="wrong")
    assert response.status_code == 400
    assert session.COOKIE not in response.headers.get("set-cookie", "")


def test_safe_021_pin_never_sent_back(client, church_ids, wrong_pin):
    for htmx in (True, False):
        assert wrong_pin not in _login(client, church_ids, wrong_pin, htmx=htmx).text


def test_ui_032_typed_values_stay_after_an_error(client, church_ids, wrong_pin):
    response = _login(client, church_ids, wrong_pin, htmx=True)
    assert 'value="Test"' in response.text and 'value="Player 1"' in response.text


def test_arch_034_logged_in_player_skips_login(client, church_ids, fake_pin):
    _login(client, church_ids, fake_pin)
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/code"
