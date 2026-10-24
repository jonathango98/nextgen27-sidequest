"""Shared Jinja2 templates, so routes can render without importing app.main."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent

# ARCH-001: Jinja2 with autoescape on. Starlette turns it on for .html templates.
templates = Jinja2Templates(directory=APP_DIR / "templates")
