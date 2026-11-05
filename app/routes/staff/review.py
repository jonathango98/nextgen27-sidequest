"""Admin review of shared takeaways (SAFE-007, SAFE-040, SAFE-041, DEC-076).
GET /admin/review and POST /admin/review/{public_id} only (API-001).
"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.auth import csrf
from app.auth.staff import CurrentStaff, require_role
from app.db import get_db
from app.forms import read_form
from app.rendering import templates
from app.services import journal

# One tab per review status, waiting first (SAFE-007).
TABS = {
    "pending": "Waiting",
    "approved": "Approved",
    "rejected": "Rejected",
    "hidden": "Hidden",
}
# What each button did, in plain words.
DONE = {
    "approve": "Approved. Players can read it on All journals.",
    "reject": "Rejected. Only the writer and admins can see it.",
    "hide": "Hidden. Players can't read it anymore.",
}

router = APIRouter()
Admin = Annotated[CurrentStaff, Depends(require_role("admin"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]


def _page(
    request: Request,
    conn: sqlite3.Connection,
    status: str,
    *,
    status_code: int = 200,
    error: journal.TakeawayRefused | None = None,
    notice: str | None = None,
) -> Response:
    # Only these tabs, so a typed-in link can't ask for anything else.
    status = status if status in TABS else "pending"
    token = csrf.token_for(request)
    context = {
        "csrf_token": token,
        "tabs": TABS,
        "status": status,
        "counts": journal.review_counts(conn),
        "notes": journal.review_queue(conn, status),
        "notice": notice,
    }
    if error:
        context |= {"error_code": error.code, "message": error.message}
    response = templates.TemplateResponse(
        request, "staff/review.html", context, status_code=status_code
    )
    csrf.set_token(response, token)
    return response


@router.get("/admin/review")
def review_queue(request: Request, staff: Admin, conn: Db, status: str = "pending"):
    return _page(request, conn, status)


@router.post("/admin/review/{public_id}", dependencies=[Depends(csrf.require_csrf)])
def review(request: Request, staff: Admin, conn: Db, form: Form, public_id: str):
    # The tab the admin was on, so the page stays there after the button.
    status = form.get("status", "pending")
    outcome = form.get("outcome", "")
    try:
        journal.review(
            conn, admin_id=staff.id, takeaway_public_id=public_id, outcome=outcome
        )
    except journal.TakeawayRefused as refused:
        return _page(request, conn, status, status_code=refused.status, error=refused)
    # API-002: the same page either way. HTMX picks out the list with hx-select.
    return _page(request, conn, status, notice=DONE[outcome])
