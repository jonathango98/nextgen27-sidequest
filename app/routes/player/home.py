"""Home page skeleton (GAME-070, UI-036). No game logic yet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


@router.get("/")
def home(request: Request, player: Player):
    return templates.TemplateResponse(
        request, "player/home.html", {"score": player.score}
    )
