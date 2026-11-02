import re

import pytest
from fastapi.testclient import TestClient

from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.main import create_app

FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=0)  # fake data (ENG-047)
VENDOR = "/static/js/vendor"
SCANNER_FILES = (
    f"{VENDOR}/barcode-detector-3.2.2.ponyfill.js",
    f"{VENDOR}/zxing-wasm-3.1.3-reader.wasm",
    "/static/js/scanner.js",
)


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    # Start the app, so pages can read the game state for the paused note (UI-033).
    with TestClient(app) as c:
        yield c


def test_arch_025_scan_page_uses_configured_format(client):
    html = client.get("/scan").text
    assert f'data-format="{load_config()["qr"]["format_version"]}"' in html


def test_ui_037_scan_page_has_camera_view_and_help_line(client):
    html = client.get("/scan").text
    assert "<video" in html
    assert 'class="scanner-guide"' in html
    assert html.count('class="scanner-help"') == 1


def test_arch_004_scan_page_loads_scripts_from_our_server(client):
    html = client.get("/scan").text
    sources = re.findall(r'(?:src|data-wasm)="([^"]+)"', html)
    assert set(SCANNER_FILES) <= set(sources)
    assert all(s.startswith("/static/") for s in sources)


@pytest.mark.parametrize("path", SCANNER_FILES)
def test_arch_004_scanner_files_are_served(client, path):
    assert client.get(path).status_code == 200


def test_arch_004_wasm_served_as_wasm(client):
    # Browsers only stream-compile a .wasm file sent with this type.
    response = client.get(f"{VENDOR}/zxing-wasm-3.1.3-reader.wasm")
    assert response.headers["content-type"] == "application/wasm"
