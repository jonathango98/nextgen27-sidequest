"""Shared Jinja2 templates, so routes can render without importing app.main."""

import hashlib
from functools import cache
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from jinja2.runtime import Context

from app.db import connect
from app.services.game_state import BANNERS, current_state

APP_DIR = Path(__file__).resolve().parent

# ARCH-001: Jinja2 with autoescape on. Starlette turns it on for .html templates.
templates = Jinja2Templates(directory=APP_DIR / "templates")


@pass_context
def game_state(context: Context) -> str:
    """The game state for this page: on, paused, or off (GAME-100)."""
    request = context.get("request")
    if request is None:  # a template rendered outside a request, as in some tests
        return "on"
    # ARCH-042: read fresh for every page, never kept between requests. Kept only for the rest of
    # this page, so the banner and the buttons always agree.
    if not hasattr(request.state, "game_state"):
        conn = connect(request.app.state.db_path)
        try:
            request.state.game_state = current_state(conn)
        finally:
            conn.close()
    return request.state.game_state


@pass_context
def game_banner(context: Context) -> str | None:
    """The paused or closed note for the top of a player page, or None while on (UI-033)."""
    return BANNERS.get(game_state(context))


@cache
def static_url(path: str) -> str:
    """A static file's URL with a fingerprint of its contents, such as /static/css/player.css?v=1a2b3c4d.

    The fingerprint changes whenever the file does, so phones fetch new styles right after a
    deploy instead of keeping an old copy. Files only change with a deploy, which restarts the app.
    """
    digest = hashlib.sha256((APP_DIR / "static" / path).read_bytes()).hexdigest()
    return f"/static/{path}?v={digest[:8]}"


templates.env.globals["static_url"] = static_url
templates.env.globals["game_state"] = game_state
templates.env.globals["game_banner"] = game_banner
