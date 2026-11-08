"""Open Box: blind boxes earned, claimed, and ready to claim (GAME-073, GAME-074)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.db import get_db
from app.rendering import templates
from app.services import blind_boxes

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]


def box_tiles(earned: int, claimed: int, cfg: dict) -> list[dict]:
    """One tile per box a player can earn, up to max_per_player (GAME-070, GAME-071).

    A box already handed over says Claimed, an earned box not yet handed over says
    Ready, and the rest show the score that unlocks them (UI-051).
    """
    tiles = []
    for n in range(1, cfg["max_per_player"] + 1):
        if n <= claimed:
            state = "claimed"
        elif n <= earned:
            state = "ready"
        else:
            state = "locked"
        tiles.append(
            {"number": n, "points": n * cfg["milestone_points"], "state": state}
        )
    return tiles


@router.get("/box")
def open_box(request: Request, player: Player, conn: Db):
    # GAME-073: this page only shows how to claim. It saves nothing and reserves no box.
    cfg = request.app.state.config["blind_box"]
    earned = blind_boxes.earned(player.score, cfg)
    claimed = blind_boxes.claimed_count(conn, player.public_id)
    context = {
        "boxes": box_tiles(earned, claimed, cfg),
        # GAME-074: earned minus claimed, never below 0. GAME-077: never a "boxes left" count.
        "ready": blind_boxes.claimable(earned, claimed),
    }
    return templates.TemplateResponse(request, "player/box.html", context)
