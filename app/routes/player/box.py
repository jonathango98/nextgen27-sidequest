"""Open Box skeleton (GAME-073). No game logic yet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


@router.get("/box")
def open_box(request: Request, player: Player):
    cfg = request.app.state.config["blind_box"]
    # Pretend number until home.pages counts earned minus claimed boxes (GAME-074).
    ready = 0
    # GAME-070, GAME-071: one box every milestone_points, up to max_per_player.
    boxes = [
        {"number": n, "points": n * cfg["milestone_points"], "ready": n <= ready}
        for n in range(1, cfg["max_per_player"] + 1)
    ]
    context = {"boxes": boxes, "ready": ready}
    return templates.TemplateResponse(request, "player/box.html", context)
