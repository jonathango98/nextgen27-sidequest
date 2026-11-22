"""Admin staff page: add an usher or admin account, switch one off or back on.

GET and POST /admin/staff only (API-001). ARCH-035, ARCH-036, ARCH-050, GAME-110, OPS-042.
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
from app.services import staff as staff_accounts

NOT_FOUND = "We couldn't find that account. Please reload the page."
SWITCHED_OFF = "{username} is switched off and can't log in."
SWITCHED_ON = "{username} is switched on and can log in again."

router = APIRouter()
Admin = Annotated[CurrentStaff, Depends(require_role("admin"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]


def _page(
    request: Request,
    conn: sqlite3.Connection,
    staff: CurrentStaff,
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
        "accounts": staff_accounts.list_accounts(conn),
        "me": staff.id,
        "username_max": staff_accounts.USERNAME_MAX_CHARS,
        "notice": notice,
        # A refused add keeps the username and role, never the password.
        "form": {k: v for k, v in (form or {}).items() if k != "password"},
    }
    if error_code:
        context |= {"error_code": error_code, "message": message}
    response = templates.TemplateResponse(
        request, "staff/admin_staff.html", context, status_code=status_code
    )
    csrf.set_token(response, token)
    return response


def _account_id(form: dict[str, str]) -> int | None:
    value = form.get("account", "")
    return int(value) if value.isdigit() else None


@router.get("/admin/staff")
def list_staff(request: Request, staff: Admin, conn: Db):
    return _page(request, conn, staff)


@router.post("/admin/staff", dependencies=[Depends(csrf.require_csrf)])
def change_staff(request: Request, staff: Admin, conn: Db, form: Form):
    # One route adds and switches accounts (API-001). The action field says which.
    action = form.get("action", "")
    if action == "add":
        try:
            staff_accounts.add_account(
                conn,
                form.get("username", ""),
                form.get("password", ""),
                form.get("role", ""),
                staff.id,
            )
        except staff_accounts.StaffAccountError as error:
            return _page(
                request,
                conn,
                staff,
                status_code=400,
                error_code="BAD_INPUT",
                message=str(error),
                form=form,
            )
        # Back to the list, so a refresh can't add the account twice.
        return RedirectResponse("/admin/staff", status_code=303)

    if action not in ("switch_off", "switch_on"):
        return _page(
            request,
            conn,
            staff,
            status_code=400,
            error_code="BAD_INPUT",
            message="Please reload the page and try again.",
        )
    account_id = _account_id(form)
    active = action == "switch_on"
    try:
        if account_id is None:
            raise staff_accounts.StaffAccountNotFound
        staff_accounts.set_active(conn, account_id, active, staff.id)
    except staff_accounts.StaffAccountNotFound:
        return _page(
            request,
            conn,
            staff,
            status_code=404,
            error_code="NOT_FOUND",
            message=NOT_FOUND,
        )
    except staff_accounts.StaffAccountError as error:
        return _page(
            request,
            conn,
            staff,
            status_code=400,
            error_code="BAD_INPUT",
            message=str(error),
        )
    username = next(
        a.username for a in staff_accounts.list_accounts(conn) if a.id == account_id
    )
    notice = (SWITCHED_ON if active else SWITCHED_OFF).format(username=username)
    # API-002: the same page either way. HTMX picks out the list with hx-select.
    return _page(request, conn, staff, notice=notice)
