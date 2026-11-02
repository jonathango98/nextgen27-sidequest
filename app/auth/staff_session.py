"""Signed staff session cookie (ARCH-034, ARCH-036, DEC-063). Separate from the player cookie.

A phone can be logged in as a player and as staff at once, and neither can stand in for the other:
the staff cookie is signed for a different purpose, so a player cookie never passes as staff.
"""

import hmac
import time

from fastapi import Request, Response

from app.auth.session import sign

# __Host- makes browsers require Secure and Path=/, and refuse a Domain, so no other site can set it.
COOKIE = "__Host-sq_staff"
PURPOSE = "staff"


def _now() -> float:
    return time.time()


def _value(staff_id: int, issued: int) -> str:
    body = f"{staff_id}.{issued}"
    return f"{body}.{sign(PURPOSE, body)}"


def set_staff_session(response: Response, staff_id: int, hours: int) -> None:
    response.set_cookie(
        COOKIE,
        _value(staff_id, int(_now())),
        max_age=hours * 60 * 60,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_staff_session(response: Response) -> None:
    # Browsers drop the cookie only when these match how it was set.
    response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")


def staff_session_id(request: Request, hours: int) -> int | None:
    value = request.cookies.get(COOKIE)
    if not value or value.count(".") != 2:
        return None
    staff_id, issued, mac = value.split(".")
    if not hmac.compare_digest(mac, sign(PURPOSE, f"{staff_id}.{issued}")):
        return None
    if not (staff_id.isascii() and staff_id.isdigit()):
        return None
    if not (issued.isascii() and issued.isdigit()):
        return None
    # DEC-063: the server checks the age itself. The cookie's max_age is only a hint to the browser.
    age = _now() - int(issued)
    if not 0 <= age < hours * 60 * 60:
        return None
    return int(staff_id)
