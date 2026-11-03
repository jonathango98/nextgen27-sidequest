"""My Code page and its refreshing QR (GAME-001, API-030, ARCH-074)."""

import sqlite3
import time
from typing import Annotated

import segno
from fastapi import APIRouter, Depends, Request
from markupsafe import Markup

from app.auth.current import CurrentPlayer, get_current_player
from app.db import get_db
from app.rendering import templates
from app.services import qr
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
        "retry_seconds": cfg["poll_retry_seconds"],  # DEC-031
    }


@router.get("/code")
def my_code(request: Request, player: Player, now: Now):
    return templates.TemplateResponse(
        request, "player/code.html", _qr_context(request, player, now), headers=NO_STORE
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
