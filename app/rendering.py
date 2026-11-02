"""Shared Jinja2 templates, so routes can render without importing app.main."""

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
def game_banner(context: Context) -> str | None:
    """The paused or closed note for the top of a player page, or None while on (UI-033)."""
    request = context.get("request")
    if request is None:  # a template rendered outside a request, as in some tests
        return None
    # ARCH-042: read on every page, never cached, so a pause shows on the very next page.
    conn = connect(request.app.state.db_path)
    try:
        return BANNERS.get(current_state(conn))
    finally:
        conn.close()


templates.env.globals["game_banner"] = game_banner
