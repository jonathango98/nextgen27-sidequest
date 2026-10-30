import itertools
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi import Request
from fastapi.responses import HTMLResponse

from app.auth import session
from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.main import create_app, templates
from app.routes.player import code
from app.services import qr

FAKE_SCORE = 120  # fake data (ENG-047), not a game number
FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=FAKE_SCORE)
# Fake data (ENG-047), never a real key (SAFE-030).
FAKE_KEY = "test-only-fake-signing-key"
FAKE_SESSION_KEY = "test-only-fake-session-key"  # never a real key (SAFE-030)
FAKE_START = 1_800_000_000  # fixed clock, not a game number
VIEWPORT_HEIGHT = 740
COMPONENTS = Path(__file__).with_name("components.html")


def _frame_app():
    app = create_app()
    rotation = app.state.config["qr"]["rotation_seconds"]
    windows = itertools.count(FAKE_START // rotation + 1)
    # Each request lands 1 second before the end of the next window, so every
    # refresh shows a new code after a 1 second wait (GAME-001, API-030).
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    app.dependency_overrides[code.current_time] = lambda: next(windows) * rotation - 1

    # Test-only route that renders the frame on its own. The real app does not have it (API-001).
    @app.get("/_test/frame")
    def frame(request: Request):
        return templates.TemplateResponse(
            request, "player/base.html", {"score": FAKE_SCORE}
        )

    # Test-only page with every look.base component (07 section 3). Not in the real app (API-001).
    @app.get("/_test/components")
    def components():
        cfg = app.state.config
        milestone = cfg["blind_box"]["milestone_points"]
        progress = FAKE_SCORE % milestone
        page = templates.env.from_string(COMPONENTS.read_text(encoding="utf-8"))
        return HTMLResponse(
            page.render(
                score=FAKE_SCORE,
                pill_points=cfg["points"]["journal_takeaway"],
                milestone=milestone,
                progress=progress,
                percent=progress * 100 // milestone,
            )
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
        "ignore_https_errors": True,  # the test server's self-signed certificate
    }


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    # HTTPS, because WebKit drops Secure cookies on plain http, which breaks the
    # __Host- CSRF and session cookies (ARCH-038). Throwaway cert, never in the repo (SAFE-030).
    cert_dir = tmp_path_factory.mktemp("tls")
    cert, key = cert_dir / "cert.pem", cert_dir / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    old_key = os.environ.get(qr.KEY_ENV)
    os.environ[qr.KEY_ENV] = FAKE_KEY
    old_session_key = os.environ.get(session.KEY_ENV)
    os.environ[session.KEY_ENV] = FAKE_SESSION_KEY
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            _frame_app(),
            host="127.0.0.1",
            port=port,
            log_level="warning",
            ssl_certfile=str(cert),
            ssl_keyfile=str(key),
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "test server did not start"
        time.sleep(0.05)
    yield f"https://127.0.0.1:{port}"
    server.should_exit = True
    thread.join()
    if old_key is None:
        del os.environ[qr.KEY_ENV]
    else:
        os.environ[qr.KEY_ENV] = old_key
    if old_session_key is None:
        del os.environ[session.KEY_ENV]
    else:
        os.environ[session.KEY_ENV] = old_session_key
