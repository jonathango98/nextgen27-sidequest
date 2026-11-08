"""Home page: score and blind box progress (GAME-070, UI-036)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth import csrf
from app.auth.current import CurrentPlayer, get_current_player
from app.db import get_db
from app.rendering import templates
from app.services import blind_boxes, leaderboards

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]


def first_name(conn: sqlite3.Connection, public_id: str) -> str | None:
    # UI-036, DEC-062: "Hi, <first name>". The player's own first name, shown only to them.
    row = conn.execute(
        "SELECT first_name FROM player WHERE public_id = ?", (public_id,)
    ).fetchone()
    return row["first_name"] if row else None


@router.get("/")
def home(request: Request, player: Player, conn: Db):
    # ARCH-038: the log out form needs a CSRF token.
    token = csrf.token_for(request)
    cfg = request.app.state.config
    context = {
        "score": player.score,
        "first_name": first_name(conn, player.public_id),
        # GAME-085, DEC-073: own place or top percent, only if the switch is on.
        "standing": leaderboards.own_standing(
            conn, cfg["leaderboard"], player.public_id
        ),
        "csrf_token": token,
        "journal_points": cfg["points"]["journal_takeaway"],
        # GAME-070, GAME-071: points since the last milestone, worked out from score.
        "box": blind_boxes.progress(player.score, cfg["blind_box"]),
    }
    response = templates.TemplateResponse(request, "player/home.html", context)
    csrf.set_token(response, token)
    return response
