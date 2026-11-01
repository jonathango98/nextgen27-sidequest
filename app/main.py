"""App factory (ARCH-008)."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.auth.csrf import CsrfFailed
from app.auth.current import LoginRequired
from app.auth.staff import StaffLoginRequired, WrongRole
from app.config import load_config
from app.db import connect, db_path_from_env, migrate
from app.forms import BadForm
from app.rendering import APP_DIR, templates
from app.routes.player import (
    box,
    code,
    home,
    join,
    journal,
    login,
    logout,
    quests,
    scan,
    wrapped,
)
from app.routes.staff import console as staff_console
from app.routes.staff import login as staff_login
from app.services import churches
from app.services.game_state import GameNotOn

# API-020: friendly message for each 423 code, from 06-api-and-screens.md section 3.
GAME_NOT_ON_MESSAGES = {
    "PAUSED": "The game is paused during the session.",
    "GAME_OFF": "The game is closed right now.",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DATA-040: migrations run at start. ARCH-010: one replica, so only one process runs them.
    app.state.db_path = db_path_from_env()
    conn = connect(app.state.db_path)
    try:
        migrate(conn)
        if churches.is_preview(os.environ.get("RAILWAY_ENVIRONMENT_NAME")):
            churches.seed_examples(conn)
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
    app.include_router(logout.router)
    app.include_router(staff_login.router)
    app.include_router(staff_console.router)
    # Screen skeleton (UI-030): plain pages, no game logic yet.
    for module in (home, scan, quests, journal, box, wrapped):
        app.include_router(module.router)

    @app.exception_handler(LoginRequired)
    def login_required(request: Request, exc: LoginRequired):
        # API-005: error partial with the error code from 06-api-and-screens.md section 3.
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"error_code": "LOGIN_REQUIRED", "message": "Please log in first."},
            status_code=401,
        )

    @app.exception_handler(StaffLoginRequired)
    def staff_login_required(request: Request, exc: StaffLoginRequired):
        # ARCH-035: a staff page while logged out goes to the staff login.
        if request.headers.get("HX-Request"):
            return Response(status_code=204, headers={"HX-Redirect": "/staff/login"})
        return RedirectResponse("/staff/login", status_code=303)

    @app.exception_handler(WrongRole)
    def wrong_role(request: Request, exc: WrongRole):
        # ARCH-035: logged in, but this page is for another role. 403 WRONG_ROLE (API-005).
        context = {
            "error_code": "WRONG_ROLE",
            "message": "This page is for admins only.",
        }
        name = (
            "partials/error.html"
            if request.headers.get("HX-Request")
            else "staff/wrong_role.html"
        )
        return templates.TemplateResponse(request, name, context, status_code=403)

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

    @app.exception_handler(GameNotOn)
    def game_not_on(request: Request, exc: GameNotOn):
        # ARCH-041, API-020: 423 is used only for PAUSED and GAME_OFF.
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "error_code": exc.error_code,
                "message": GAME_NOT_ON_MESSAGES[exc.error_code],
            },
            status_code=423,
        )

    @app.get("/health", response_class=PlainTextResponse)
    def health() -> str:
        # DEC-029: no database check, no version or environment details.
        return "ok"

    return app


app = create_app()
