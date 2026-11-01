"""Staff log in (ARCH-036, DEC-061). GET and POST /staff/login only (API-001)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.auth import csrf
from app.auth.login import LoginError
from app.auth.staff import StaffLoginRequired, get_current_staff
from app.auth.staff_login import USERNAME_MAX_CHARS, log_in_staff
from app.auth.staff_session import set_staff_session
from app.db import get_db
from app.forms import read_form
from app.rendering import templates

# ARCH-035: where each role lands after logging in.
HOME = {"usher": "/usher", "admin": "/admin"}

router = APIRouter()
Db = Annotated[sqlite3.Connection, Depends(get_db)]
# Read in an async dependency, so the route is a plain def and hashes off the event loop.
Form = Annotated[dict[str, str], Depends(read_form)]


def _render(
    request: Request, form: dict[str, str], error: LoginError | None = None
) -> Response:
    token = csrf.token_for(request)
    context = {"csrf_token": token, "form": form, "username_max": USERNAME_MAX_CHARS}
    if error:
        context |= {"error": True, "error_code": error.code, "message": error.message}
    # API-002: HTMX gets only the form, a normal browser gets the whole page.
    name = (
        "staff/partials/login_form.html"
        if request.headers.get("HX-Request")
        else "staff/login.html"
    )
    response = templates.TemplateResponse(
        request, name, context, status_code=error.status if error else 200
    )
    csrf.set_token(response, token)
    return response


@router.get("/staff/login")
def login_page(request: Request):
    try:
        staff = get_current_staff(request)
    except StaffLoginRequired:
        return _render(request, {})
    return RedirectResponse(HOME[staff.role], status_code=303)


@router.post("/staff/login", dependencies=[Depends(csrf.require_csrf)])
def login_submit(request: Request, conn: Db, form: Form):
    kept = {"username": form.get("username", "")}  # never the password (ARCH-036)
    try:
        staff_id, role = log_in_staff(conn, form)
    except LoginError as error:
        return _render(request, kept, error)

    if request.headers.get("HX-Request"):
        response: Response = Response(
            status_code=204, headers={"HX-Redirect": HOME[role]}
        )
    else:
        response = RedirectResponse(HOME[role], status_code=303)
    hours = request.app.state.config["auth"]["staff_session_hours"]
    set_staff_session(response, staff_id, hours)
    return response
