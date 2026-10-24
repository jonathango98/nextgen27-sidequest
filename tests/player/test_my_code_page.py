from playwright.sync_api import Page, expect

from app.config import load_config

REFRESH_TIMEOUT_MS = 5000  # test wait, not a game number


def test_game_001_my_code_shows_large_qr(page: Page, live_server):
    page.goto(f"{live_server}/code")
    panel = page.locator(".qr-panel svg")
    expect(panel).to_be_visible()
    content_width = page.evaluate("document.querySelector('.content').clientWidth")
    assert panel.bounding_box()["width"] >= content_width / 2
    expect(page.get_by_text("brightness")).to_be_visible()


def test_api_030_my_code_swaps_in_new_code(page: Page, live_server):
    page.goto(f"{live_server}/code")
    path = page.locator(".qr-panel svg path")
    first = path.get_attribute("d")
    expect(path).not_to_have_attribute("d", first, timeout=REFRESH_TIMEOUT_MS)


def test_ui_002_my_code_has_no_sideways_scroll(page: Page, live_server):
    page.goto(f"{live_server}/code")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]


def test_eng_045_my_code_has_no_console_errors(page: Page, live_server):
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{live_server}/code")
    page.wait_for_load_state("networkidle")
    assert errors == []
