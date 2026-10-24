"""CSRF protection for every POST (ARCH-038, API-004).

A random token sits in a cookie. Each form sends it back in a hidden field, and HTMX sends it
in a header set once on the page. Another site cannot read the cookie, so it cannot send a match.
"""

import hmac
import secrets

from fastapi import Request, Response

from app.forms import read_form

COOKIE = "__Host-sq_csrf"
FIELD = "csrf_token"
HEADER = "X-CSRF-Token"


class CsrfFailed(Exception):
    pass


def token_for(request: Request) -> str:
    return request.cookies.get(COOKIE) or secrets.token_urlsafe(32)


def set_token(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE, token, path="/", secure=True, httponly=True, samesite="lax"
    )


async def require_csrf(request: Request) -> None:
    expected = request.cookies.get(COOKIE)
    sent = request.headers.get(HEADER) or (await read_form(request)).get(FIELD)
    if (
        not expected
        or not isinstance(sent, str)
        or not hmac.compare_digest(expected, sent)
    ):
        raise CsrfFailed
