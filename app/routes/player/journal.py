"""Journal: write a private takeaway and list your own (GAME-030 to GAME-036).

The Summary page is still a skeleton until journal.share-review (GAME-031, SAFE-009, SAFE-017).
"""

import sqlite3
from itertools import groupby
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.auth import csrf
from app.auth.current import CurrentPlayer, get_current_player
from app.db import get_db
from app.forms import read_form
from app.rendering import templates
from app.routes.player.scan import player_id
from app.services import journal
from app.services.game_state import GAME_NOT_ON_MESSAGES, GameNotOn

router = APIRouter()

Player = Annotated[CurrentPlayer, Depends(get_current_player)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
Form = Annotated[dict[str, str], Depends(read_form)]

# The note on the Journal page after saving: with points, or a later note with none (DEC-072).
SAVED = ("points", "extra")

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
def my_takeaways(request: Request, player: Player, conn: Db):
    saved = request.query_params.get("saved")
    # Only the player's own notes (03 section 3: a private takeaway is Own), one group per
    # session in the order list_own gives.
    notes = journal.list_own(conn, player_id(conn, player))
    context = {
        "sessions": [
            {"title": title, "notes": [n.text for n in group]}
            for title, group in groupby(notes, key=lambda n: n.session_title)
        ],
        # Only these values, so a typed-in link can't show a made-up message.
        "saved": saved if saved in SAVED else None,
        "journal_points": request.app.state.config["points"]["journal_takeaway"],
    }
    return templates.TemplateResponse(request, "player/journal.html", context)


def _render_form(
    request: Request,
    conn: sqlite3.Connection,
    player: CurrentPlayer,
    form: dict[str, str],
    error: tuple[int, str, str] | None = None,
) -> Response:
    cfg = request.app.state.config
    token = csrf.token_for(request)
    choices = journal.sessions_to_write(
        conn,
        player_id(conn, player),
        require_checkin=cfg["journal"]["require_checkin"],  # GAME-035
    )
    context = {
        "csrf_token": token,
        "choices": choices,
        "picked": form.get("session") or (choices[0].public_id if choices else ""),
        "text": form.get("text", ""),
        "min_words": cfg["limits"]["journal_min_words"],  # GAME-030
        "journal_points": cfg["points"]["journal_takeaway"],  # UI-039
    }
    status = 200
    if error:
        status, code, message = error
        context |= {"error": True, "error_code": code, "message": message}
    # API-002: HTMX gets only the form, a normal browser gets the whole page.
    name = (
        "player/partials/journal_form.html"
        if request.headers.get("HX-Request")
        else "player/journal_new.html"
    )
    response = templates.TemplateResponse(request, name, context, status_code=status)
    csrf.set_token(response, token)
    return response


@router.get("/journal/new")
def new_takeaway(request: Request, player: Player, conn: Db):
    return _render_form(request, conn, player, {})


@router.post("/journal", dependencies=[Depends(csrf.require_csrf)])
def submit_takeaway(request: Request, player: Player, conn: Db, form: Form):
    cfg = request.app.state.config
    try:
        saved = journal.submit(
            conn,
            player_id=player_id(conn, player),
            session_public_id=form.get("session", ""),
            text=form.get("text", ""),
            min_words=cfg["limits"]["journal_min_words"],
            amount=cfg["points"]["journal_takeaway"],
            require_checkin=cfg["journal"]["require_checkin"],
        )
    except journal.TakeawayRefused as refused:
        error = (refused.status, refused.code, refused.message)
        return _render_form(request, conn, player, form, error)
    except GameNotOn as exc:
        # GAME-033: keep what they typed, so it can be sent once the game is back on.
        error = (423, exc.error_code, GAME_NOT_ON_MESSAGES[exc.error_code])
        return _render_form(request, conn, player, form, error)
    target = f"/journal?saved={SAVED[0] if saved.points else SAVED[1]}"
    if request.headers.get("HX-Request"):
        return Response(status_code=204, headers={"HX-Redirect": target})
    return RedirectResponse(target, status_code=303)


@router.get("/summary")
def summary(request: Request, player: Player):
    # SAFE-017: signed-in players only, so it needs the player like every page here.
    return templates.TemplateResponse(
        request, "player/summary.html", {"sessions": PLACEHOLDER_SUMMARY}
    )
