"""My Code page, its refreshing QR, and the note when someone scans it (GAME-001, API-030, API-032)."""

import sqlite3
import time
from typing import Annotated

import segno
from fastapi import APIRouter, Depends, Request, Response
from markupsafe import Markup

from app.auth.current import CurrentPlayer, get_current_player
from app.db import get_db
from app.rendering import templates
from app.routes.player.scan import player_id
from app.services import connections, qr
from app.services.game_state import GameNotOn, current_state

# The QR standard's minimum quiet zone, in modules. Not a game number.
QUIET_ZONE = 4

# Codes go stale, so no browser or proxy may keep a copy (GAME-001).
NO_STORE = {"Cache-Control": "no-store"}

router = APIRouter()


def current_time() -> float:
    return time.time()


Player = Annotated[CurrentPlayer, Depends(get_current_player)]
Now = Annotated[float, Depends(current_time)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]


def qr_svg(payload: str) -> Markup:
    # segno builds the SVG from our own payload only, so it is safe to insert as is.
    svg = segno.make(payload).svg_inline(
        border=QUIET_ZONE, omitsize=True, title="My Code"
    )
    return Markup(svg)


def _qr_context(request: Request, player: CurrentPlayer, now: float) -> dict:
    cfg = request.app.state.config["qr"]
    payload = qr.payload(qr.PLAYER_KIND, player.public_id, now, cfg)
    return {
        "qr_svg": qr_svg(payload),
        "refresh_seconds": qr.seconds_left(
            now, cfg, qr.refresh_offset(player.public_id, cfg)
        ),
        # UI-037: the timer bar drains over the whole window, starting from where this code is.
        "rotation_seconds": cfg["rotation_seconds"],
        "retry_seconds": cfg["poll_retry_seconds"],  # DEC-031
    }


def _incoming_context(request: Request, since: int, after: int, notes: list) -> dict:
    return {
        "since": since,
        "after": after,
        "notes": notes,
        "poll_seconds": request.app.state.config["qr"]["incoming_poll_seconds"],
    }


@router.get("/code")
def my_code(request: Request, player: Player, conn: Db, now: Now):
    # API-032: only scans after the page opened get a note.
    latest = connections.latest_id(conn, player_id(conn, player))
    context = _qr_context(request, player, now) | _incoming_context(
        request, latest, latest, []
    )
    return templates.TemplateResponse(
        request, "player/code.html", context, headers=NO_STORE
    )


@router.get("/code/qr")
def my_code_qr(request: Request, player: Player, now: Now, conn: Db):
    # DEC-068: no code while paused. An open My Code page swaps this 423 in at its next refresh,
    # so the code disappears without a reload (API-006).
    if current_state(conn) == "paused":
        raise GameNotOn("PAUSED")
    # API-002, API-003: only the fragment that HTMX swaps in.
    return templates.TemplateResponse(
        request,
        "player/partials/code_qr.html",
        _qr_context(request, player, now),
        headers=NO_STORE,
    )


@router.get("/code/incoming")
def my_code_incoming(
    request: Request, player: Player, conn: Db, since: int = 0, after: int = 0
):
    # API-032: 204 when nobody new scanned this code, so the page keeps what it shows.
    # Otherwise every note since the page opened, and the newest id to check after.
    me = player_id(conn, player)
    notes = connections.incoming(conn, me, since)
    newest = max((note.id for note in notes), default=0)
    if newest <= after:
        return Response(status_code=204, headers=NO_STORE)
    return templates.TemplateResponse(
        request,
        "player/partials/code_incoming.html",
        _incoming_context(request, since, newest, notes),
        headers=NO_STORE,
    )
