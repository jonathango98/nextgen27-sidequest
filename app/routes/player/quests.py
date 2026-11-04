"""Quests page (GAME-070, UI-036). Look only: progress is pretend until home.pages."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


def quest_list(cfg: dict) -> list[dict]:
    """Every quest and its points, from game-config.yaml (AI-013). Progress is pretend."""
    points = cfg["points"]
    per_day = cfg["limits"]["photobooth_per_day"]
    return [
        # GAME-010: someone from another church. The new church bonus comes on top (GAME-011).
        {
            "title": "Connect",
            "how": "Scan, answer",
            "progress": "0 friends",
            "points": points["connect_other_church"],
        },
        # GAME-022: the first check-in tier, for coming early.
        {
            "title": "Session check-in",
            "how": "Come early",
            "progress": "0 done",
            "points": cfg["checkin"]["tier_points"][0],
        },
        {
            "title": "Journal",
            "how": "Each session",
            "progress": "0 done",
            "points": points["journal_takeaway"],
        },  # GAME-030
        {
            "title": "Booths",
            "how": "Each booth",
            "progress": "0 done",
            "points": points["booth_visit"],
        },  # GAME-041
        {
            "title": "Photobooth",
            "how": f"{per_day} a day",
            "progress": f"0 / {per_day}",
            "points": points["photobooth"],
        },  # GAME-042
        {
            "title": "Hidden items",
            "how": "Find them",
            "progress": "None yet",
            "points": points["hidden_item"],
        },  # GAME-043
        # GAME-040: every player on this page has joined. home.pages checks the join award itself.
        {
            "title": "Join the game",
            "how": "Welcome!",
            "progress": "Earned",
            "points": points["join"],
            "done": True,
        },
    ]


@router.get("/quests")
def quests(request: Request, player: Player):
    context = {"quests": quest_list(request.app.state.config)}
    return templates.TemplateResponse(request, "player/quests.html", context)
