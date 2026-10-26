"""Log in (ARCH-032, SAFE-022). GET and POST /login only (API-001)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.auth import csrf, signup
from app.auth.login import LoginError, log_in
from app.auth.session import session_public_id, set_session
from app.db import get_db
from app.forms import read_form
from app.rendering import templates

# Where a player lands after logging in: Home.
AFTER_LOGIN = "/"
FORM_FIELDS = ("first_name", "last_name", "church_id")

router = APIRouter()
Db = Annotated[sqlite3.Connection, Depends(get_db)]
# Read in an async dependency, so the route is a plain def and hashes off the event loop.
Form = Annotated[dict[str, str], Depends(read_form)]


def _render(
    request: Request,
    conn: sqlite3.Connection,
    form: dict[str, str],
    error: LoginError | None = None,
) -> Response:
    token = csrf.token_for(request)
    context = {
        "csrf_token": token,
        "form": form,
        "churches": signup.churches(conn),
        "name_max": signup.NAME_MAX_CHARS,
        "pin_digits": request.app.state.config["auth"]["pin_digits"],
    }
    if error:
        context |= {"error": True, "error_code": error.code, "message": error.message}
    # API-002: HTMX gets only the form, a normal browser gets the whole page.
    name = (
        "player/partials/login_form.html"
        if request.headers.get("HX-Request")
        else "player/login.html"
    )
    response = templates.TemplateResponse(
        request, name, context, status_code=error.status if error else 200
    )
    csrf.set_token(response, token)
    return response


@router.get("/login")
def login_page(request: Request, conn: Db):
    if session_public_id(request):
        return RedirectResponse(AFTER_LOGIN, status_code=303)
    return _render(request, conn, {})


@router.post("/login", dependencies=[Depends(csrf.require_csrf)])
def login_submit(request: Request, conn: Db, form: Form):
    kept = {k: form.get(k, "") for k in FORM_FIELDS}  # never the PIN (SAFE-021)
    try:
        public_id = log_in(conn, form, request.app.state.config["auth"])
    except LoginError as error:
        return _render(request, conn, kept, error)

    if request.headers.get("HX-Request"):
        response: Response = Response(
            status_code=204, headers={"HX-Redirect": AFTER_LOGIN}
        )
    else:
        response = RedirectResponse(AFTER_LOGIN, status_code=303)
    set_session(response, public_id)
    return response
