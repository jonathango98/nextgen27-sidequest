"""App factory (ARCH-008)."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import load_config
from app.db import connect, db_path_from_env, migrate

APP_DIR = Path(__file__).resolve().parent

# ARCH-001: Jinja2 with autoescape on. Starlette turns it on for .html templates.
templates = Jinja2Templates(directory=APP_DIR / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DATA-040: migrations run at start. ARCH-010: one replica, so only one process runs them.
    app.state.db_path = db_path_from_env()
    conn = connect(app.state.db_path)
    try:
        migrate(conn)
    finally:
        conn.close()
    yield


def create_app() -> FastAPI:
    # API-001: only routes in 06-api-and-screens.md, so FastAPI's built-in docs pages are off.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.config = load_config()
    # ARCH-010: the app serves its own static files.
    app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

    @app.get("/health", response_class=PlainTextResponse)
    def health() -> str:
        # DEC-029: no database check, no version or environment details.
        return "ok"

    return app


app = create_app()
