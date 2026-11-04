"""Admin sessions page: add, edit, and End session (DATA-014, GAME-021, GAME-026, GAME-110).
GET and POST /admin/sessions, and POST /admin/sessions/{public_id}/end only (API-001).
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
from app.services import game_state, sessions

NOT_FOUND = "We couldn't find that session. Please reload the page."
# GAME-026: what End session did, in plain words.
ENDED_RESUMED = "{title} has ended. The game is on again, and takeaways are open."
ENDED = "{title} has ended. Takeaways are open."
ENDED_OFF = "{title} has ended. Takeaways are open. The game is still off."
ALREADY_ENDED = "{title} had already ended. Nothing changed."

router = APIRouter()
Admin = Annotated[CurrentStaff, Depends(require_role("admin"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]


def _start_label(starts_at: str, timezone: str) -> str:
    local = sessions.to_local(starts_at, timezone)
    hour = local.hour % 12 or 12
    return f"{local:%a %b} {local.day}, {hour}:{local:%M} {local:%p}"


def _row(session: sessions.Session, timezone: str) -> dict:
    row = {"session": session, "start_label": None, "start_value": ""}
    if session.starts_at:
        row["start_label"] = _start_label(session.starts_at, timezone)
        row["start_value"] = sessions.to_local(session.starts_at, timezone).strftime(
            sessions.LOCAL_INPUT_FORMAT
        )
    return row


def _page(
    request: Request,
    conn: sqlite3.Connection,
    *,
    status_code: int = 200,
    error_code: str | None = None,
    message: str | None = None,
    notice: str | None = None,
    form: dict[str, str] | None = None,
) -> Response:
    timezone = request.app.state.config["game"]["timezone"]
    token = csrf.token_for(request)
    context = {
        "csrf_token": token,
        "state": game_state.current_state(conn),
        "rows": [_row(s, timezone) for s in sessions.list_all(conn)],
        "title_max": sessions.TITLE_MAX_CHARS,
        "notice": notice,
        # Typed values come back after a refused form, so the admin doesn't type them again.
        "form": form or {},
    }
    if error_code:
        context |= {"error_code": error_code, "message": message}
    response = templates.TemplateResponse(
        request, "staff/sessions.html", context, status_code=status_code
    )
    csrf.set_token(response, token)
    return response


@router.get("/admin/sessions")
def list_sessions(request: Request, staff: Admin, conn: Db):
    return _page(request, conn)


@router.post("/admin/sessions", dependencies=[Depends(csrf.require_csrf)])
def save_session(request: Request, staff: Admin, conn: Db, form: Form):
    # One route adds and edits (API-001): an edit form names its session.
    public_id = form.get("session", "")
    try:
        details = sessions.read_details(
            form, request.app.state.config["game"]["timezone"]
        )
        if public_id:
            sessions.edit(conn, public_id, details, staff.id)
        else:
            sessions.add(conn, details, staff.id)
    except sessions.SessionError as error:
        return _page(
            request,
            conn,
            status_code=400,
            error_code="BAD_INPUT",
            message=str(error),
            form=form,
        )
    except sessions.SessionNotFound:
        return _page(
            request, conn, status_code=404, error_code="NOT_FOUND", message=NOT_FOUND
        )
    # Back to the list, so a refresh can't add the session twice.
    return RedirectResponse("/admin/sessions", status_code=303)


@router.post(
    "/admin/sessions/{public_id}/end", dependencies=[Depends(csrf.require_csrf)]
)
def end_session(request: Request, staff: Admin, conn: Db, public_id: str):
    try:
        result = sessions.end(conn, public_id, staff.id)
    except sessions.SessionNotFound:
        return _page(
            request, conn, status_code=404, error_code="NOT_FOUND", message=NOT_FOUND
        )
    if not result.ended:
        notice = ALREADY_ENDED
    elif result.resumed:
        notice = ENDED_RESUMED
    elif game_state.current_state(conn) == "off":
        notice = ENDED_OFF
    else:
        notice = ENDED
    # API-002: the same page either way. HTMX picks out the list with hx-select.
    return _page(request, conn, notice=notice.format(title=result.title))
