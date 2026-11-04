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


# Fake notes until journal.notes lists the player's own notes (GAME-031). Obviously fake
# (SAFE-031). Newest session first, each with who can read it and where its review is (SAFE-007).
PLACEHOLDER_NOTES = [
    {
        "session": "Example Session 3",
        "text": "Example takeaway: I want to pray before I scroll in the morning, even for one minute.",
        "status": "Just me",
    },
    {
        "session": "Example Session 2",
        "text": "Example takeaway: listening first stuck with me. I'll ask more questions in small group.",
        "status": "With name · In review",
    },
    {
        "session": "Example Session 1",
        "text": "Example takeaway: serving isn't about the stage. I'll help set up chairs without being asked.",
        "status": "Anonymous · Shared",
    },
]


@router.get("/journal")
def my_takeaways(request: Request, player: Player):
    context = {
        "notes": PLACEHOLDER_NOTES,
        "journal_points": request.app.state.config["points"]["journal_takeaway"],
    }
    return templates.TemplateResponse(request, "player/journal.html", context)


@router.get("/journal/new")
def new_takeaway(request: Request, player: Player):
    cfg = request.app.state.config
    context = {
        # Pretend session until journal.notes offers the ended sessions (GAME-036).
        "session_name": PLACEHOLDER_SUMMARY[-1]["session"],
        "min_words": cfg["limits"]["journal_min_words"],  # GAME-030
        "journal_points": cfg["points"]["journal_takeaway"],  # UI-039
    }
    return templates.TemplateResponse(request, "player/journal_new.html", context)


@router.get("/summary")
def summary(request: Request, player: Player):
    # SAFE-017: signed-in players only, so it needs the player like every page here.
    return templates.TemplateResponse(
        request, "player/summary.html", {"sessions": PLACEHOLDER_SUMMARY}
    )
