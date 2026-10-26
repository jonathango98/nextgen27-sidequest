"""Scanner and icebreaker skeletons (ARCH-025, GAME-017, UI-037). No game logic yet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


@router.get("/scan")
def scanner(request: Request, player: Player):
    return templates.TemplateResponse(
        request, "player/scan.html", {"score": player.score}
    )


@router.get("/connections/{connection_id}")
def icebreaker(request: Request, player: Player, connection_id: int):
    # Placeholder for any id. The Scanner feature checks the player is in this pair (SAFE-006).
    return templates.TemplateResponse(
        request, "player/icebreaker.html", {"score": player.score}
    )
