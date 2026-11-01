"""Log out on this phone only (ARCH-034, DEC-061). POST /logout only (API-001)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.auth import csrf, staff_session
from app.auth.session import clear_session

# Where the next person who picks up the phone lands.
AFTER_LOGOUT = "/login"
AFTER_STAFF_LOGOUT = "/staff/login"

router = APIRouter()


@router.post("/logout", dependencies=[Depends(csrf.require_csrf)])
def logout(request: Request):
    # Clears only this browser's cookies, so the player's other phones stay logged in.
    # A staff phone goes back to the staff login (DEC-061).
    target = (
        AFTER_STAFF_LOGOUT
        if request.cookies.get(staff_session.COOKIE)
        else AFTER_LOGOUT
    )
    if request.headers.get("HX-Request"):
        response: Response = Response(status_code=204, headers={"HX-Redirect": target})
    else:
        response = RedirectResponse(target, status_code=303)
    clear_session(response)
    staff_session.clear_staff_session(response)
    return response
