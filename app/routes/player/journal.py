"""Journal and Summary page skeletons (GAME-031, SAFE-009, SAFE-017). No game logic yet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]

# Fake note cards until journal.share-review shows the approved shared takeaways (UI-038).
# Obviously fake (SAFE-031). Newest session first, first name and church only, or Anonymous (SAFE-004).
PLACEHOLDER_SUMMARY = [
    {
        "session": "Example Session 2",
        "takeaways": [
            {
                "text": "Example takeaway: I want to listen first this week and ask more questions in small group.",
                "first_name": "Test",
                "church": "Example Church A",
            },
            {
                "text": "Example takeaway: showing up for my friends matters more than having the right words.",
                "anonymous": True,
            },
        ],
    },
    {
        "session": "Example Session 1",
        "takeaways": [
            {
                "text": "Example takeaway: serving doesn't need a stage. I'll help set up before youth group.",
                "first_name": "Test",
                "church": "Example Church B",
            },
        ],
    },
]


@router.get("/journal")
def my_takeaways(request: Request, player: Player):
    return templates.TemplateResponse(
        request, "player/journal.html", {"score": player.score}
    )


@router.get("/journal/new")
def new_takeaway(request: Request, player: Player):
    return templates.TemplateResponse(
        request, "player/journal_new.html", {"score": player.score}
    )


@router.get("/summary")
def summary(request: Request, player: Player):
    # SAFE-017: signed-in players only, so it needs the player like every page here.
    return templates.TemplateResponse(
        request,
        "player/summary.html",
        {"score": player.score, "sessions": PLACEHOLDER_SUMMARY},
    )
