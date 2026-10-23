import socket
import threading
import time

import pytest
import uvicorn
from fastapi import Request

from app.config import load_config
from app.main import create_app, templates

FAKE_SCORE = 120  # fake data (ENG-047), not a game number
VIEWPORT_HEIGHT = 740


def _frame_app():
    app = create_app()

    # Test-only route that renders the frame on its own. The real app does not have it (API-001).
    @app.get("/_test/frame")
    def frame(request: Request):
        return templates.TemplateResponse(
            request, "player/base.html", {"score": FAKE_SCORE}
        )

    return app


@pytest.fixture
def fake_score():
    return FAKE_SCORE


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    return {
        **browser_context_args,
        "viewport": {"width": width, "height": VIEWPORT_HEIGHT},
    }


@pytest.fixture(scope="session")
def live_server():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(_frame_app(), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "test server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join()
