"""Log out on this phone only (ARCH-034). POST /logout only (API-001)."""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.auth import csrf
from app.auth.session import clear_session

# Where the next person who picks up the phone lands.
AFTER_LOGOUT = "/login"

router = APIRouter()


@router.post("/logout", dependencies=[Depends(csrf.require_csrf)])
def logout():
    # Clears only this browser's cookie, so the player's other phones stay logged in.
    response = RedirectResponse(AFTER_LOGOUT, status_code=303)
    clear_session(response)
    return response
