"""Usher tools: find a player by name or by scanning My Code (GAME-112, GAME-113, DEC-065).
GET /usher/players and POST /usher/scan only (API-001).
"""

import sqlite3
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth import csrf
from app.auth.staff import CurrentStaff, require_role
from app.db import get_db
from app.forms import read_form
from app.rendering import templates
from app.services import players

# These pages show player names, so a shared phone's browser must not keep a copy.
NO_STORE = {"Cache-Control": "no-store"}

router = APIRouter()


def current_time() -> float:
    return time.time()


Usher = Annotated[CurrentStaff, Depends(require_role("usher"))]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]
Now = Annotated[float, Depends(current_time)]


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


@router.post("/usher/scan", dependencies=[Depends(csrf.require_csrf)])
def scan_player(request: Request, staff: Usher, conn: Db, form: Form, now: Now):
    # API-002: only the fragment, swapped in under the camera.
    try:
        picked = players.from_scan(
            conn, form.get("payload", ""), now, request.app.state.config["qr"]
        )
    except players.ScanRefused as refused:
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"error_code": refused.code, "message": refused.message},
            status_code=refused.status,
            headers=NO_STORE,
        )
    return templates.TemplateResponse(
        request,
        "staff/partials/player_card.html",
        {"picked": picked},
        headers=NO_STORE,
    )
