"""Journal and Summary page skeletons (GAME-031, SAFE-009, SAFE-017). No game logic yet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


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
        request, "player/summary.html", {"score": player.score}
    )
