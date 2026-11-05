"""App factory (ARCH-008)."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.access_log import keep_queries_out_of_log
from app.auth.csrf import CsrfFailed
from app.auth.current import LoginRequired
from app.auth.rate_limit import RateLimiter
from app.auth.session import SessionKeyMissing, session_public_id
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
from app.routes.screen import views as screen_views
from app.routes.staff import console as staff_console
from app.routes.staff import login as staff_login
from app.routes.staff import sessions as staff_sessions
from app.routes.staff import usher as staff_usher
from app.services import churches, connections, leaderboards, players, sessions, staff
from app.services.game_state import GAME_NOT_ON_MESSAGES, GameNotOn


@asynccontextmanager
async def lifespan(app: FastAPI):
    keep_queries_out_of_log()  # ARCH-051
    # DATA-040: migrations run at start. ARCH-010: one replica, so only one process runs them.
    app.state.db_path = db_path_from_env()
    conn = connect(app.state.db_path)
    try:
        migrate(conn)
        if churches.is_preview(os.environ.get("RAILWAY_ENVIRONMENT_NAME")):
            churches.seed_examples(conn)
            staff.seed_preview(conn)
            players.seed_preview(conn, app.state.config)
            connections.seed_preview(conn, app.state.config)
            sessions.seed_preview(conn)
            leaderboards.seed_preview(conn, app.state.config)
    finally:
        conn.close()
    yield


def _logged_in(request: Request) -> bool:
    # Cookie only, no database, so this works even when the database is what failed.
    try:
        return session_public_id(request) is not None
    except SessionKeyMissing:
        return False


def _error_page(
    request: Request, status: int, error_code: str | None, title: str, message: str
) -> Response:
    context = {"error_code": error_code, "message": message}
    if request.headers.get("HX-Request"):
        # API-005: HTMX swaps in the small partial, not a whole page.
        return templates.TemplateResponse(
            request, "partials/error.html", context, status_code=status
        )
    context |= {"title": title, "logged_in": _logged_in(request)}
    return templates.TemplateResponse(
        request, "error.html", context, status_code=status
    )


def create_app() -> FastAPI:
    # API-001: only routes in 06-api-and-screens.md, so FastAPI's built-in docs pages are off.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.config = load_config()
    leaderboards.check_config(app.state.config["leaderboard"])
    app.state.rate_limiter = RateLimiter()  # ARCH-031
    # ARCH-010: the app serves its own static files.
    app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
    app.include_router(code.router)
    app.include_router(join.router)
    app.include_router(login.router)
    app.include_router(logout.router)
    app.include_router(staff_login.router)
    app.include_router(staff_console.router)
    app.include_router(staff_usher.router)
    app.include_router(screen_views.router)
    app.include_router(staff_sessions.router)
    # Screen skeleton (UI-030): plain pages, no game logic yet.
    for module in (home, scan, quests, journal, box, wrapped):
        app.include_router(module.router)

    @app.exception_handler(LoginRequired)
    def login_required(request: Request, exc: LoginRequired):
        # DEC-061: straight to the login page, no error. HTMX would swap a 303's
        # login page into the target, so HTMX gets HX-Redirect instead (API-002).
        if request.headers.get("HX-Request"):
            return Response(status_code=204, headers={"HX-Redirect": "/login"})
        return RedirectResponse("/login", status_code=303)

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

    @app.exception_handler(StarletteHTTPException)
    async def not_found(request: Request, exc: StarletteHTTPException):
        # API-005, API-021: 404 NOT_FOUND gets a friendly page. Other HTTP errors keep the default.
        if exc.status_code != 404:
            return await http_exception_handler(request, exc)
        return _error_page(
            request, 404, "NOT_FOUND", "Page not found", "We couldn't find that."
        )

    @app.exception_handler(Exception)
    def server_error(request: Request, exc: Exception):
        # A crash shows no details to the phone. The server still logs it.
        return _error_page(
            request, 500, None, "Something went wrong", "Please try again in a minute."
        )

    @app.get("/health", response_class=PlainTextResponse)
    def health() -> str:
        # DEC-029: no database check, no version or environment details.
        return "ok"

    return app


app = create_app()
