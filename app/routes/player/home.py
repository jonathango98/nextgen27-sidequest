"""Home page skeleton (GAME-070, UI-036). No game logic yet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth import csrf
from app.auth.current import CurrentPlayer, get_current_player
from app.rendering import templates

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]


@router.get("/")
def home(request: Request, player: Player):
    # ARCH-038: the log out form needs a CSRF token.
    token = csrf.token_for(request)
    cfg = request.app.state.config
    context = {
        "score": player.score,
        "csrf_token": token,
        "journal_points": cfg["points"]["journal_takeaway"],
        "box_milestone": cfg["blind_box"]["milestone_points"],
        # Pretend number until home.pages shows the real progress (GAME-070).
        "box_progress": 0,
    }
    response = templates.TemplateResponse(request, "player/home.html", context)
    csrf.set_token(response, token)
    return response
