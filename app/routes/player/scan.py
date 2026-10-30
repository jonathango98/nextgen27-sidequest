"""Scanner page (ARCH-025, UI-037) and the icebreaker skeleton (GAME-017)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


@router.get("/scan")
def scanner(request: Request, player: Player):
    # ARCH-025: the page only accepts codes that start with this version.
    qr_format = request.app.state.config["qr"]["format_version"]
    return templates.TemplateResponse(
        request, "player/scan.html", {"score": player.score, "qr_format": qr_format}
    )


@router.get("/connections/{connection_id}")
def icebreaker(request: Request, player: Player, connection_id: int):
    # Placeholder for any id. The Scanner feature checks the player is in this pair (SAFE-006).
    return templates.TemplateResponse(
        request, "player/icebreaker.html", {"score": player.score}
    )
