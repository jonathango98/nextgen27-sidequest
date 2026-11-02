import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, rate_limit, session, signup
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.staff import create_account
from tests.conftest import make_fake_pin

# Fake data only (ENG-047, SAFE-030). Addresses are from the documentation ranges.
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
CHURCH = "Example Church A"
ADMIN = ("test-admin-1", "test password only 1")
PHONE_IP = "203.0.113.7"
OTHER_IP = "198.51.100.9"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def limiter(clock):
    return rate_limit.RateLimiter(clock)


@pytest.fixture
def login_limit(cfg_auth):
    return cfg_auth["login_ip_limit_per_minute"]


@pytest.fixture
def signup_limit(cfg_auth):
    return cfg_auth["signup_ip_limit_per_minute"]


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "rate-limit.db"


@pytest.fixture
def church_id(db_path):
    return {}


@pytest.fixture
def client(monkeypatch, db_path, church_id, fake_pin):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    with TestClient(create_app(), base_url="https://testserver") as c:
        conn = connect(db_path)
        church_id["id"] = conn.execute(
            "INSERT INTO church (name) VALUES (?)", (CHURCH,)
        ).lastrowid
        details = signup.Details("Test", "Player 1", church_id["id"], False)
        signup.create_player(conn, details, fake_pin, load_config())
        create_account(conn, *ADMIN, "admin")
        conn.close()
        c.get("/login")  # sets the CSRF cookie
        yield c


@pytest.fixture
def wrong_pin(cfg_auth):
    return make_fake_pin(cfg_auth["pin_digits"], start=5)


def _fill(client, kind, ip):
    # Use up an IP's tries straight in the limiter, so tests skip slow PIN hashing.
    limit = client.app.state.config["auth"][rate_limit.LIMIT_KEYS[kind]]
    for _ in range(limit):
        assert client.app.state.rate_limiter.allow(kind, ip, limit)


def _post(client, path, data, ip=PHONE_IP):
    return client.post(
        path,
        data={"csrf_token": client.cookies.get(csrf.COOKIE), **data},
        headers={"HX-Request": "true", "X-Real-IP": ip},
        follow_redirects=False,
    )


def _login(client, church_id, pin, ip=PHONE_IP):
    data = {
        "first_name": "Test",
        "last_name": "Player 1",
        "church_id": str(church_id["id"]),
        "pin": pin,
    }
    return _post(client, "/login", data, ip)


def _error_code(response):
    match = re.search(r'data-error-code="([A-Z_]+)"', response.text)
    return match and match.group(1)


def _player(db_path):
    conn = connect(db_path)
    row = conn.execute("SELECT * FROM player").fetchone()
    conn.close()
    return row


def test_arch_031_login_limited_per_ip(limiter, login_limit):
    for _ in range(login_limit):
        assert limiter.allow("login", PHONE_IP, login_limit)
    assert not limiter.allow("login", PHONE_IP, login_limit)


def test_arch_031_other_ip_not_limited(limiter, login_limit):
    for _ in range(login_limit):
        limiter.allow("login", PHONE_IP, login_limit)
    assert limiter.allow("login", OTHER_IP, login_limit)


def test_arch_031_signup_has_own_higher_limit(limiter, login_limit, signup_limit):
    assert signup_limit > login_limit
    for _ in range(login_limit):
        limiter.allow("login", PHONE_IP, login_limit)
    for _ in range(signup_limit):
        assert limiter.allow("signup", PHONE_IP, signup_limit)
    assert not limiter.allow("signup", PHONE_IP, signup_limit)


def test_arch_031_window_resets_after_a_minute(limiter, clock, login_limit):
    for _ in range(login_limit):
        limiter.allow("login", PHONE_IP, login_limit)
    clock.now += rate_limit.WINDOW_SECONDS - 1
    assert not limiter.allow("login", PHONE_IP, login_limit)
    clock.now += 1
    assert limiter.allow("login", PHONE_IP, login_limit)


def test_arch_031_refused_tries_do_not_extend_the_wait(limiter, clock, login_limit):
    for _ in range(login_limit):
        limiter.allow("login", PHONE_IP, login_limit)
    for _ in range(login_limit):
        clock.now += 0.5
        assert not limiter.allow("login", PHONE_IP, login_limit)
    clock.now = 1000.0 + rate_limit.WINDOW_SECONDS
    assert limiter.allow("login", PHONE_IP, login_limit)


def test_arch_031_old_ips_are_forgotten(limiter, clock, login_limit):
    limiter.allow("login", PHONE_IP, login_limit)
    clock.now += rate_limit.WINDOW_SECONDS + 1
    limiter.allow("login", OTHER_IP, login_limit)
    assert list(limiter._hits) == [("login", OTHER_IP)]


def test_arch_031_changing_forwarded_for_does_not_dodge_the_limit(
    client, church_id, wrong_pin
):
    # On Railway the last X-Forwarded-For entry is a rotating edge node. X-Real-IP is the client.
    _fill(client, "login", PHONE_IP)
    data = {
        "csrf_token": client.cookies.get(csrf.COOKIE),
        "first_name": "Test",
        "last_name": "Player 1",
        "church_id": str(church_id["id"]),
        "pin": wrong_pin,
    }
    headers = {"X-Real-IP": PHONE_IP, "X-Forwarded-For": f"{PHONE_IP}, {OTHER_IP}"}
    response = client.post("/login", data=data, headers=headers)
    assert response.status_code == rate_limit.STATUS
    assert _error_code(response) == rate_limit.CODE


def test_arch_031_login_over_limit_gets_rate_limited(
    client, church_id, wrong_pin, db_path
):
    _fill(client, "login", PHONE_IP)
    response = _login(client, church_id, wrong_pin)
    assert response.status_code == rate_limit.STATUS
    assert _error_code(response) == rate_limit.CODE
    assert rate_limit.MESSAGE in response.text
    # The PIN was never checked, so the account's wrong-PIN count did not move.
    assert _player(db_path)["failed_pin_attempts"] == 0


def test_arch_031_login_from_other_ip_still_works(client, church_id, fake_pin):
    _fill(client, "login", PHONE_IP)
    response = _login(client, church_id, fake_pin, ip=OTHER_IP)
    assert response.status_code == 204


def test_arch_031_staff_login_over_limit_gets_rate_limited(client):
    _fill(client, "staff_login", PHONE_IP)
    data = {"username": ADMIN[0], "password": ADMIN[1]}
    response = _post(client, "/staff/login", data)
    assert response.status_code == rate_limit.STATUS
    assert _error_code(response) == rate_limit.CODE


def test_arch_031_signup_over_limit_saves_nothing(client, church_id, fake_pin):
    _fill(client, "signup", PHONE_IP)
    details = {
        "first_name": "Test",
        "last_name": "Player 2",
        "church_id": str(church_id["id"]),
        "age_18_plus": "yes",
    }
    # The details step is not a sign-up, so it still moves on to the PIN step.
    assert _post(client, "/join", {"step": "details", **details}).status_code == 200
    data = {"step": "pin", **details, "pin": fake_pin, "pin_again": fake_pin}
    response = _post(client, "/join", data)
    assert response.status_code == rate_limit.STATUS
    assert _error_code(response) == rate_limit.CODE
    conn = connect(client.app.state.db_path)
    assert conn.execute("SELECT COUNT(*) FROM player").fetchone()[0] == 1
    conn.close()


def test_safe_022_lockout_still_applies_across_ips(
    client, church_id, wrong_pin, cfg_auth, db_path
):
    # The account lockout counts wrong PINs from every address, not per IP.
    for i in range(cfg_auth["pin_max_attempts"]):
        _login(client, church_id, wrong_pin, ip=f"192.0.2.{i + 1}")
    assert _player(db_path)["locked_at"] is not None
