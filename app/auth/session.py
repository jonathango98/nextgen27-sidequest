"""Signed session cookie (ARCH-034). The key lives only in SQ_SESSION_KEY on the server."""

import base64
import hashlib
import hmac
import os

from fastapi import Request, Response

KEY_ENV = "SQ_SESSION_KEY"
# __Host- makes browsers require Secure and Path=/, and refuse a Domain, so no other site can set it.
COOKIE = "__Host-sq_session"
# ARCH-034: at least until Wrapped closes. The retention date is OPEN (SAFE-014), so use the
# longest lifetime browsers allow, 400 days. Not a game number.
MAX_AGE_SECONDS = 400 * 24 * 60 * 60


class SessionKeyMissing(Exception):
    pass


def _key() -> bytes:
    value = os.environ.get(KEY_ENV)
    if not value:
        raise SessionKeyMissing(f"{KEY_ENV} is not set")
    return value.encode()


def sign(purpose: str, value: str) -> str:
    mac = hmac.new(_key(), f"{purpose}:{value}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).rstrip(b"=").decode()


def set_session(response: Response, public_id: str) -> None:
    response.set_cookie(
        COOKIE,
        f"{public_id}.{sign('session', public_id)}",
        max_age=MAX_AGE_SECONDS,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def session_public_id(request: Request) -> str | None:
    value = request.cookies.get(COOKIE)
    if not value or "." not in value:
        return None
    public_id, mac = value.rsplit(".", 1)
    if not hmac.compare_digest(mac, sign("session", public_id)):
        return None
    return public_id
