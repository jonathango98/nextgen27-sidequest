import hashlib
import re

from fastapi.testclient import TestClient

from app.main import create_app
from app.rendering import APP_DIR, static_url, templates

HEAD_FILES = ("css/tokens.css", "css/player.css", "js/htmx.min.js")


def _fingerprint(path):
    return hashlib.sha256((APP_DIR / "static" / path).read_bytes()).hexdigest()[:8]


def test_ui_004_static_urls_carry_a_fingerprint_of_the_file():
    for path in HEAD_FILES:
        assert static_url(path) == f"/static/{path}?v={_fingerprint(path)}"


def test_ui_004_different_files_get_different_fingerprints():
    assert (
        static_url("css/tokens.css").split("?v=")[1]
        != static_url("css/player.css").split("?v=")[1]
    )


def test_ui_004_every_player_page_links_fingerprinted_files():
    html = templates.get_template("player/head.html").render()
    for path in HEAD_FILES:
        assert f"/static/{path}?v={_fingerprint(path)}" in html
    assert not re.search(
        r'(href|src)="/static/(css/[a-z]+\.css|js/htmx\.min\.js)"', html
    )


def test_arch_010_fingerprinted_file_is_still_served():
    client = TestClient(create_app())
    response = client.get(static_url("css/player.css"))
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
