"""Scanner page (ARCH-025, UI-037), saving a scan (GAME-014), and the icebreaker (GAME-017)."""

import sqlite3
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth import csrf
from app.auth.current import CurrentPlayer, LoginRequired, get_current_player
from app.db import get_db
from app.forms import read_form
from app.rendering import templates
from app.services import connections

router = APIRouter()


def current_time() -> float:
    return time.time()


Player = Annotated[CurrentPlayer, Depends(get_current_player)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]
Now = Annotated[float, Depends(current_time)]


def player_id(conn: sqlite3.Connection, player: CurrentPlayer) -> int:
    row = conn.execute(
        "SELECT id FROM player WHERE public_id = ?", (player.public_id,)
    ).fetchone()
    if row is None:
        raise LoginRequired
    return row["id"]


@router.get("/scan")
def scanner(request: Request, player: Player):
    token = csrf.token_for(request)
    # ARCH-025: the page only accepts codes that start with this version.
    qr_format = request.app.state.config["qr"]["format_version"]
    response = templates.TemplateResponse(
        request, "player/scan.html", {"qr_format": qr_format, "csrf_token": token}
    )
    csrf.set_token(response, token)
    return response


@router.post("/scan", dependencies=[Depends(csrf.require_csrf)])
def scan_submit(request: Request, player: Player, conn: Db, form: Form, now: Now):
    # API-002: only the result fragment, swapped in under the camera.
    try:
        met = connections.scan(
            conn,
            scanner_public_id=player.public_id,
            payload=form.get("payload", ""),
            now=now,
            config=request.app.state.config,
        )
    except connections.ScanRefused as refused:
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"error_code": refused.code, "message": refused.message},
            status_code=refused.status,
        )
    return templates.TemplateResponse(
        request, "player/partials/scan_result.html", {"connection": met}
    )


@router.get("/connections/{connection_id}")
def icebreaker(request: Request, player: Player, conn: Db, connection_id: int):
    met = connections.for_player(conn, connection_id, player_id(conn, player))
    # SAFE-006: someone outside the pair gets the same 404 as a missing id.
    return templates.TemplateResponse(
        request,
        "player/icebreaker.html",
        {
            "connection": met,
            "error_code": "NOT_FOUND",
            "message": "We couldn't find that.",
        },
        status_code=200 if met else 404,
    )
