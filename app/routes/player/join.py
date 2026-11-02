"""Join and PIN set (SAFE-002, SAFE-021, ARCH-034). GET and POST /join only (API-001)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.auth import csrf, signup
from app.auth.session import session_public_id, set_session
from app.db import get_db
from app.forms import read_form
from app.rendering import templates
from app.services.game_state import current_state

# Where a player lands after joining: Home.
AFTER_JOIN = "/"
STEPS = {
    "details": "player/partials/join_details.html",
    "pin": "player/partials/join_pin.html",
}
FORM_FIELDS = ("first_name", "last_name", "church_id", "age_18_plus")
# GAME-108: shown instead of the form while the game is off, so nobody types it all for nothing.
CLOSED = "Sign-up is closed right now."

router = APIRouter()
Db = Annotated[sqlite3.Connection, Depends(get_db)]


# Read the form in an async dependency, so the route can be a plain def and hash the PIN
# in a worker thread instead of on the event loop.
Form = Annotated[dict[str, str], Depends(read_form)]


def _render(
    request: Request,
    conn: sqlite3.Connection,
    step: str,
    form: dict[str, str],
    error: signup.SignupError | None = None,
) -> Response:
    token = csrf.token_for(request)
    context = {
        "step_template": STEPS[step],
        "csrf_token": token,
        "form": form,
        "churches": signup.churches(conn),
        "name_max": signup.NAME_MAX_CHARS,
        "pin_digits": request.app.state.config["auth"]["pin_digits"],
    }
    if error:
        context |= {"error": True, "error_code": error.code, "message": error.message}
    # API-002: HTMX gets only the step, a normal browser gets the whole page.
    name = STEPS[step] if request.headers.get("HX-Request") else "player/join.html"
    response = templates.TemplateResponse(
        request, name, context, status_code=error.status if error else 200
    )
    csrf.set_token(response, token)
    return response


@router.get("/join")
def join_page(request: Request, conn: Db):
    if session_public_id(request):
        return RedirectResponse(AFTER_JOIN, status_code=303)
    if current_state(conn) == "off":
        return templates.TemplateResponse(
            request, "player/join.html", {"closed": CLOSED}
        )
    return _render(request, conn, "details", {})


@router.post("/join", dependencies=[Depends(csrf.require_csrf)])
def join_submit(request: Request, conn: Db, form: Form):
    kept = {k: form.get(k, "") for k in FORM_FIELDS}  # never the PIN (SAFE-021)

    # Back on the PIN step: show step 1 again with what was typed (UI-032). Nothing is saved.
    if form.get("back"):
        return _render(request, conn, "details", kept)

    try:
        details = signup.check_details(conn, form)
    except signup.SignupError as error:
        return _render(request, conn, "details", kept, error)
    if form.get("step") != "pin":
        return _render(request, conn, "pin", kept)

    config = request.app.state.config
    try:
        pin = signup.check_pin(form, config["auth"]["pin_digits"])
        public_id = signup.create_player(conn, details, pin, config)
    except signup.SignupError as error:
        return _render(
            request,
            conn,
            "pin" if error.code == "BAD_INPUT" else "details",
            kept,
            error,
        )

    # POST /join logs the player in.
    if request.headers.get("HX-Request"):
        response: Response = Response(
            status_code=204, headers={"HX-Redirect": AFTER_JOIN}
        )
    else:
        response = RedirectResponse(AFTER_JOIN, status_code=303)
    set_session(response, public_id)
    return response
