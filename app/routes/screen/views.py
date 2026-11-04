"""The main screen (ARCH-037, UI-040, UI-044, API-031, DEC-069).
GET /screen and the view partials in 06-api-and-screens.md only (API-001).

No login: every page needs the screen key (ARCH-037). The views say coming soon until their own
pieces fill them in: `leaderboards.screen`, `recap.screen`, and `screen.photobooth`.
"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.auth.screen_key import PARAM, require_screen_key
from app.db import get_db
from app.rendering import templates
from app.services import main_screen

VIEW = "screen/partials/view.html"
# ARCH-037: never send the link, key and all, to another site, and stay out of search results.
HEADERS = {
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex",
    "Cache-Control": "no-store",
}

router = APIRouter()
Key = Annotated[str, Depends(require_screen_key)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]


def _render(
    request: Request, conn: sqlite3.Connection, key: str, view: str, name: str
) -> Response:
    shown = main_screen.showing(conn, view)
    cfg = request.app.state.config["main_screen"]
    context = {
        "view": shown,
        # UI-040: while the game is off, keep asking for the first view, so the screen comes back
        # on its own when the game starts again.
        "next": main_screen.VIEWS[0]
        if shown in main_screen.OFF_VIEWS
        else main_screen.next_view(view),
        "key": key,
        "param": PARAM,
        "rotate_seconds": cfg["rotate_seconds"],  # API-031
        "min_text": cfg["min_text_px_1080p"],  # UI-041
        "min_row": cfg["min_row_px_1080p"],  # UI-041
    }
    return templates.TemplateResponse(request, name, context, headers=HEADERS)


@router.get("/screen")
def screen(request: Request, key: Key, conn: Db):
    return _render(request, conn, key, main_screen.VIEWS[0], "screen/screen.html")


def _view_route(view: str):
    def view_partial(request: Request, key: Key, conn: Db):
        return _render(request, conn, key, view, VIEW)

    return view_partial


for _view in main_screen.VIEWS:
    router.add_api_route(f"/screen/{_view}", _view_route(_view), methods=["GET"])
