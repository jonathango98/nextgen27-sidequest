"""Journal: write a takeaway, choose who can read it, and list your own (GAME-030 to GAME-036).

The Summary page shows approved shared takeaways to signed-in players (GAME-031, SAFE-007,
SAFE-009, SAFE-017, DEC-076).
"""

import sqlite3
from itertools import groupby
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
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

# GAME-031: who can read a note, in the words the picker and the note cards use.
VISIBILITY_LABELS = {
    "private": "Just me",
    "shared_named": "Shared with my name",
    "shared_anonymous": "Shared anonymously",
}

# The note on the Journal page after saving: with points, or a later note with none (DEC-072).
SAVED = ("points", "extra")


def _journal_page(
    request: Request,
    conn: sqlite3.Connection,
    player: CurrentPlayer,
    *,
    saved: str | None = None,
    error_note: str | None = None,
    error: tuple[int, str, str] | None = None,
) -> Response:
    token = csrf.token_for(request)
    # Only the player's own notes (03 section 3: a private takeaway is Own), one group per
    # session in the order list_own gives.
    notes = journal.list_own(conn, player_id(conn, player))
    context = {
        "csrf_token": token,
        "sessions": [
            {"title": title, "notes": list(group)}
            for title, group in groupby(notes, key=lambda n: n.session_title)
        ],
        # Only these values, so a typed-in link can't show a made-up message.
        "saved": saved if saved in SAVED else None,
        "journal_points": request.app.state.config["points"]["journal_takeaway"],
        "visibility_labels": VISIBILITY_LABELS,
    }
    status = 200
    if error:
        status, code, message = error
        context |= {"error_note": error_note, "error_code": code, "message": message}
    response = templates.TemplateResponse(
        request, "player/journal.html", context, status_code=status
    )
    csrf.set_token(response, token)
    return response


@router.get("/journal")
def my_takeaways(request: Request, player: Player, conn: Db):
    return _journal_page(request, conn, player, saved=request.query_params.get("saved"))


@router.post(
    "/journal/{public_id}/visibility", dependencies=[Depends(csrf.require_csrf)]
)
def change_visibility(
    request: Request, player: Player, conn: Db, form: Form, public_id: str
):
    """Change who can read one of your own notes (GAME-031, DEC-076)."""
    own_id = player_id(conn, player)
    htmx = request.headers.get("HX-Request")
    error = None
    try:
        journal.change_visibility(
            conn,
            player_id=own_id,
            takeaway_public_id=public_id,
            visibility=form.get("visibility", ""),
            review_scope=request.app.state.config["journal"]["review_scope"],
        )
    except journal.TakeawayRefused as refused:
        if refused.code == "NOT_FOUND":
            # Someone else's note looks like no note. HTMX gets only the message for the card.
            if not htmx:
                raise HTTPException(404)
            return templates.TemplateResponse(
                request,
                "partials/error.html",
                {"error_code": refused.code, "message": refused.message},
                status_code=404,
            )
        error = (refused.status, refused.code, refused.message)
    except GameNotOn as exc:
        error = (423, exc.error_code, GAME_NOT_ON_MESSAGES[exc.error_code])  # DEC-076
    if not htmx:
        if error:
            return _journal_page(
                request, conn, player, error_note=public_id, error=error
            )
        return RedirectResponse("/journal", status_code=303)
    # API-002: HTMX gets only this note's card, with the message or a Saved note.
    note = next(n for n in journal.list_own(conn, own_id) if n.public_id == public_id)
    token = csrf.token_for(request)
    context = {
        "csrf_token": token,
        "note": note,
        "visibility_labels": VISIBILITY_LABELS,
        "changed": error is None,
    }
    status = 200
    if error:
        status, code, message = error
        context |= {"error": True, "error_code": code, "message": message}
    response = templates.TemplateResponse(
        request, "player/partials/note_card.html", context, status_code=status
    )
    csrf.set_token(response, token)
    return response


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
        # GAME-031: private unless they choose.
        "visibility": form.get("visibility", "private"),
        "visibility_labels": VISIBILITY_LABELS,
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
            visibility=form.get("visibility", ""),
            review_scope=cfg["journal"]["review_scope"],  # SAFE-008
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
def summary(request: Request, player: Player, conn: Db):
    # SAFE-017: signed-in players only, so it needs the player like every page here.
    # UI-038: approved shared notes only, one group per session, newest session first.
    notes = journal.list_approved(conn)
    sessions = [
        {"title": title, "notes": list(group)}
        for title, group in groupby(notes, key=lambda n: n.session_title)
    ]
    return templates.TemplateResponse(
        request, "player/summary.html", {"sessions": sessions}
    )
