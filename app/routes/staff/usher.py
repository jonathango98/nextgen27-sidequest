"""Usher tools: find a player by name (GAME-112, GAME-113). GET /usher/players only (API-001)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.staff import CurrentStaff, require_role
from app.db import get_db
from app.rendering import templates
from app.services import players

# These pages show player names, so a shared phone's browser must not keep a copy.
NO_STORE = {"Cache-Control": "no-store"}

router = APIRouter()
Usher = Annotated[CurrentStaff, Depends(require_role("usher"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]


@router.get("/usher/players")
def find_player(
    request: Request, staff: Usher, conn: Db, q: str = "", player: str = ""
):
    query = players.clean_query(q)
    context = {"q": query, "query_max": players.QUERY_MAX_CHARS}
    status_code = 200
    if player:
        context["picked"] = players.find(conn, player)
        if context["picked"] is None:
            status_code = 404
            context |= {"error_code": "NOT_FOUND", "message": "We couldn't find that."}
    elif query:
        context["results"], context["more"] = players.search(conn, query)
    return templates.TemplateResponse(
        request,
        "staff/players.html",
        context,
        status_code=status_code,
        headers=NO_STORE,
    )
