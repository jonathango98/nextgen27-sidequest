"""Admin church list page: add a church, fix a church's name, hide one from sign-up or show it.

GET and POST /admin/churches only (API-001). SAFE-002, ARCH-050, GAME-110.
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
from app.services import churches

NOT_FOUND = "We couldn't find that church. Please reload the page."
HIDDEN = "{name} is hidden from the sign-up list. Players who already joined it can still log in."
SHOWN = "{name} is back in the sign-up list."

router = APIRouter()
Admin = Annotated[CurrentStaff, Depends(require_role("admin"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]


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
    token = csrf.token_for(request)
    context = {
        "csrf_token": token,
        "churches": churches.list_all(conn),
        "name_max": churches.NAME_MAX_CHARS,
        "notice": notice,
        # Typed values come back after a refused form, so the admin doesn't type them again.
        "form": form or {},
    }
    if error_code:
        context |= {"error_code": error_code, "message": message}
    response = templates.TemplateResponse(
        request, "staff/admin_churches.html", context, status_code=status_code
    )
    csrf.set_token(response, token)
    return response


@router.get("/admin/churches")
def list_churches(request: Request, staff: Admin, conn: Db):
    return _page(request, conn)


@router.post("/admin/churches", dependencies=[Depends(csrf.require_csrf)])
def change_church(request: Request, staff: Admin, conn: Db, form: Form):
    # One route adds, renames, hides and shows (API-001). A rename form names its church.
    church = form.get("church", "")
    name = form.get("name", "")
    action = form.get("action", "")
    if action in ("hide", "show"):
        return _hide_or_show(request, conn, staff, church, action == "hide")
    try:
        if church:
            if not church.isdigit():
                raise churches.ChurchNotFound
            churches.rename_church(conn, int(church), name, staff.id)
        else:
            churches.add_church(conn, name, staff.id)
    except churches.ChurchListError as error:
        return _page(
            request,
            conn,
            status_code=400,
            error_code="BAD_INPUT",
            message=str(error),
            form=form,
        )
    except churches.ChurchNotFound:
        return _page(
            request, conn, status_code=404, error_code="NOT_FOUND", message=NOT_FOUND
        )
    # Back to the list, so a refresh can't add the church twice.
    return RedirectResponse("/admin/churches", status_code=303)


def _hide_or_show(
    request: Request,
    conn: sqlite3.Connection,
    staff: CurrentStaff,
    church: str,
    hidden: bool,
) -> Response:
    try:
        if not church.isdigit():
            raise churches.ChurchNotFound
        churches.set_hidden(conn, int(church), hidden, staff.id)
    except churches.ChurchNotFound:
        return _page(
            request, conn, status_code=404, error_code="NOT_FOUND", message=NOT_FOUND
        )
    name = next(c.name for c in churches.list_all(conn) if c.id == int(church))
    notice = (HIDDEN if hidden else SHOWN).format(name=name)
    # API-002: the same page either way. HTMX picks out the list with hx-select.
    return _page(request, conn, notice=notice)
