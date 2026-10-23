"""App factory (ARCH-008)."""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.config import load_config


def create_app() -> FastAPI:
    # API-001: only routes in 06-api-and-screens.md, so FastAPI's built-in docs pages are off.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.config = load_config()

    @app.get("/health", response_class=PlainTextResponse)
    def health() -> str:
        # DEC-029: no database check, no version or environment details.
        return "ok"

    return app


app = create_app()
