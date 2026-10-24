"""App factory (ARCH-008)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.auth.csrf import CsrfFailed
from app.auth.current import LoginRequired
from app.config import load_config
from app.db import connect, db_path_from_env, migrate
from app.forms import BadForm
from app.rendering import APP_DIR, templates
from app.routes.player import code, join, login


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
    app.include_router(code.router)
    app.include_router(join.router)
    app.include_router(login.router)

    @app.exception_handler(LoginRequired)
    def login_required(request: Request, exc: LoginRequired):
        # API-005: error partial with the error code from 06-api-and-screens.md section 3.
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"error_code": "LOGIN_REQUIRED", "message": "Please log in first."},
            status_code=401,
        )

    @app.exception_handler(BadForm)
    @app.exception_handler(CsrfFailed)
    def csrf_failed(request: Request, exc: Exception):
        # ARCH-038: no matching token. Usually an old tab, so the message says to reload.
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "error_code": "BAD_INPUT",
                "message": "This page is out of date. Please reload it and try again.",
            },
            status_code=400,
        )

    @app.get("/health", response_class=PlainTextResponse)
    def health() -> str:
        # DEC-029: no database check, no version or environment details.
        return "ok"

    return app


app = create_app()
