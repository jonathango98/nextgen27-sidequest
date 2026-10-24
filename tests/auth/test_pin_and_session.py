import pytest
from fastapi import Response
from starlette.requests import Request

from app.auth import pin, session

FAKE_KEY = "test-only-fake-session-key"  # never a real key (SAFE-030)


def test_safe_021_pin_hash_verifies_and_hides_the_pin(fake_pin):
    stored = pin.hash_pin(fake_pin)
    assert fake_pin not in stored
    assert stored.startswith("scrypt$")
    assert pin.verify_pin(fake_pin, stored)
    assert not pin.verify_pin(fake_pin[::-1] + "0", stored)


def test_arch_030_same_pin_hashes_differently_each_time(fake_pin):
    assert pin.hash_pin(fake_pin) != pin.hash_pin(fake_pin)


def test_safe_021_pin_must_be_exactly_the_configured_digits(cfg_auth, fake_pin):
    digits = cfg_auth["pin_digits"]
    assert pin.is_valid(fake_pin, digits)
    arabic_indic = "".join(chr(0x0660 + int(c)) for c in fake_pin)
    for bad in (fake_pin[:-1], fake_pin + "1", "a" + fake_pin[1:], arabic_indic, ""):
        assert not pin.is_valid(bad, digits), bad


def _request_with_cookie(value: str) -> Request:
    header = f"{session.COOKIE}={value}".encode()
    return Request({"type": "http", "headers": [(b"cookie", header)]})


def test_arch_034_session_cookie_flags(monkeypatch):
    monkeypatch.setenv(session.KEY_ENV, FAKE_KEY)
    response = Response()
    session.set_session(response, "testpid01")
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{session.COOKIE}=testpid01.")
    for flag in (
        "Secure",
        "HttpOnly",
        "SameSite=lax",
        "Path=/",
        f"Max-Age={session.MAX_AGE_SECONDS}",
    ):
        assert flag in cookie
    assert "Domain" not in cookie


def test_arch_034_signed_cookie_round_trips(monkeypatch):
    monkeypatch.setenv(session.KEY_ENV, FAKE_KEY)
    value = f"testpid01.{session.sign('session', 'testpid01')}"
    assert session.session_public_id(_request_with_cookie(value)) == "testpid01"


@pytest.mark.parametrize("value", ["testpid01", "testpid02.bad", ""])
def test_arch_034_unsigned_or_tampered_cookie_refused(monkeypatch, value):
    monkeypatch.setenv(session.KEY_ENV, FAKE_KEY)
    if value == "testpid02.bad":
        value = f"testpid02.{session.sign('session', 'testpid01')}"
    assert session.session_public_id(_request_with_cookie(value)) is None


def test_arch_034_cookie_from_another_key_refused(monkeypatch):
    monkeypatch.setenv(session.KEY_ENV, "other-fake-key")
    value = f"testpid01.{session.sign('session', 'testpid01')}"
    monkeypatch.setenv(session.KEY_ENV, FAKE_KEY)
    assert session.session_public_id(_request_with_cookie(value)) is None


def test_arch_034_key_missing_is_an_error(monkeypatch):
    monkeypatch.delenv(session.KEY_ENV, raising=False)
    with pytest.raises(session.SessionKeyMissing):
        session.sign("session", "testpid01")
