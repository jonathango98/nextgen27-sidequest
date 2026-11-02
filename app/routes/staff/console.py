"""Usher and admin consoles (ARCH-035), and the admin's game switch (GAME-101, GAME-110).
GET /usher, GET /admin, and POST /admin/game-state only (API-001). The other tools come with
their own pieces, such as usher.console.
"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.auth import csrf
from app.auth.staff import CurrentStaff, require_role
from app.db import get_db
from app.forms import read_form
from app.rendering import templates
from app.services import game_state

PANEL = "staff/partials/game_state.html"
BAD_STATE = "Please pick Start, Pause, or Off."

router = APIRouter()
Usher = Annotated[CurrentStaff, Depends(require_role("usher"))]
Admin = Annotated[CurrentStaff, Depends(require_role("admin"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]


def _console(
    request: Request,
    staff: CurrentStaff,
    page: str,
    conn: sqlite3.Connection | None = None,
    error: str | None = None,
) -> Response:
    token = csrf.token_for(request)
    context = {"csrf_token": token, "staff": staff, "page": page}
    if conn is not None:
        context["state"] = game_state.current_state(conn)
    if error:
        context |= {"error_code": "BAD_INPUT", "message": error}
    # API-002: HTMX gets only the game panel, a normal browser gets the whole console.
    name = PANEL if request.headers.get("HX-Request") else "staff/console.html"
    response = templates.TemplateResponse(
        request, name, context, status_code=400 if error else 200
    )
    csrf.set_token(response, token)
    return response


@router.get("/usher")
def usher_console(request: Request, staff: Usher):
    return _console(request, staff, "usher")


@router.get("/admin")
def admin_console(request: Request, staff: Admin, conn: Db):
    return _console(request, staff, "admin", conn)


@router.post("/admin/game-state", dependencies=[Depends(csrf.require_csrf)])
def set_game_state(request: Request, staff: Admin, conn: Db, form: Form):
    states = request.app.state.config["game"]["states"]
    try:
        game_state.change(conn, form.get("state", ""), staff.id, states)
    except game_state.UnknownState:
        return _console(request, staff, "admin", conn, BAD_STATE)
    if request.headers.get("HX-Request"):
        return _console(request, staff, "admin", conn)
    return RedirectResponse("/admin", status_code=303)
