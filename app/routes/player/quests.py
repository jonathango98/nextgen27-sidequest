"""Quests page: every quest, its points, and the player's progress (GAME-070, UI-036)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.db import get_db
from app.rendering import templates
from app.services import journal, points

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]


def quest_list(cfg: dict, done: dict[str, int] | None = None) -> list[dict]:
    """Every quest and its points, from game-config.yaml (AI-013, ENG-031).

    `done` is how many awards the player has had per ledger reason (points.award_counts).
    Quests whose pieces do not pay points yet show 0 until those pieces count them here.
    """
    done = done or {}
    pts = cfg["points"]
    per_day = cfg["limits"]["photobooth_per_day"]
    joined = done.get(points.JOIN_REASON, 0) > 0
    return [
        # GAME-010: someone from another church. The new church bonus comes on top (GAME-011).
        # Counted here once connections.answers pays points.
        {
            "title": "Connect",
            "how": "Scan, answer",
            "progress": "0 friends",
            "points": pts["connect_other_church"],
        },
        # GAME-022: the first check-in tier, for coming early. Counted once check-in pays points.
        {
            "title": "Session check-in",
            "how": "Come early",
            "progress": "0 done",
            "points": cfg["checkin"]["tier_points"][0],
        },
        # GAME-030: one paid note per session.
        {
            "title": "Journal",
            "how": "Each session",
            "progress": f"{done.get(journal.REASON, 0)} done",
            "points": pts["journal_takeaway"],
        },
        # GAME-041, GAME-042, GAME-043: counted once their pieces pay points.
        {
            "title": "Booths",
            "how": "Each booth",
            "progress": "0 done",
            "points": pts["booth_visit"],
        },
        {
            "title": "Photobooth",
            "how": f"{per_day} a day",
            "progress": f"0 / {per_day}",
            "points": pts["photobooth"],
        },
        {
            "title": "Hidden items",
            "how": "Find them",
            "progress": "None yet",
            "points": pts["hidden_item"],
        },
        # GAME-040: done once the join award is in the ledger.
        {
            "title": "Join the game",
            "how": "Welcome!",
            "progress": "Earned" if joined else "Not yet",
            "points": pts["join"],
            "done": joined,
        },
    ]


@router.get("/quests")
def quests(request: Request, player: Player, conn: Db):
    done = points.award_counts(conn, player.public_id)
    context = {"quests": quest_list(request.app.state.config, done)}
    return templates.TemplateResponse(request, "player/quests.html", context)
