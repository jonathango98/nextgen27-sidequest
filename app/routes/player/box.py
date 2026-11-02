"""Open Box skeleton (GAME-073). No game logic yet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


@router.get("/box")
def open_box(request: Request, player: Player):
    return templates.TemplateResponse(request, "player/box.html")
