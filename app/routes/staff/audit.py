"""Admin views of the audit log (ARCH-050) and unusual activity (ARCH-062).
GET /admin/audit and GET /admin/activity only (API-001). Both only read: nothing here writes.
"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.staff import CurrentStaff, require_role
from app.db import get_db
from app.rendering import templates
from app.services import audit, connections, sessions

TABS = {"/admin/audit": "Log", "/admin/activity": "Activity"}

router = APIRouter()
Admin = Annotated[CurrentStaff, Depends(require_role("admin"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]


def _when(created_at: str, timezone: str) -> str:
    # GAME-105: staff read times in venue time. Seconds help line up quick bursts.
    local = sessions.to_local(created_at, timezone)
    hour = local.hour % 12 or 12
    return f"{local:%a %b} {local.day}, {hour}:{local:%M:%S} {local:%p}"


def _page(request: Request, tab: str, context: dict):
    context |= {"tabs": TABS, "tab": tab}
    return templates.TemplateResponse(request, "staff/audit.html", context)


@router.get("/admin/audit")
def audit_log(request: Request, staff: Admin, conn: Db, before: str = ""):
    timezone = request.app.state.config["game"]["timezone"]
    # A typed-in link with a bad value shows the newest page, not an error (like Review's tabs).
    entries, older = audit.recent(conn, int(before) if before.isdigit() else None)
    rows = [(e, _when(e.created_at, timezone)) for e in entries]
    return _page(request, "/admin/audit", {"rows": rows, "older": older})


@router.get("/admin/activity")
def activity(request: Request, staff: Admin, conn: Db):
    return _page(request, "/admin/activity", {"busy": connections.most_connected(conn)})
