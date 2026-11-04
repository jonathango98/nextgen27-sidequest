from urllib.parse import quote

import pytest
from playwright.sync_api import Browser, Page, expect

from app.auth import screen_key
from app.config import load_config
from app.db import connect
from app.services.game_state import set_state
from app.services.staff import create_account

FAKE_SCREEN_KEY = "test-only-fake-screen-key"  # never a real key (SAFE-030)
FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)
CFG = load_config()
HD = {"width": 1920, "height": 1080}  # UI-041 states its sizes at 1920x1080


@pytest.fixture(autouse=True)
def screen_on(monkeypatch, test_db_path):
    # The test server reads the key on every request, so setting it here is enough.
    monkeypatch.setenv(screen_key.KEY_ENV, FAKE_SCREEN_KEY)
    _set(test_db_path, "on")
    yield
    _set(test_db_path, "on")


def _set(test_db_path, state):
    conn = connect(test_db_path)
    try:
        set_state(conn, state)
    finally:
        conn.close()


def _url(live_server):
    return f"{live_server}/screen?{screen_key.PARAM}={quote(FAKE_SCREEN_KEY)}"


def _errors(page: Page):
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    return errors


def _px(page: Page, selector: str, prop: str) -> float:
    value = page.locator(selector).evaluate(
        f"e => getComputedStyle(e).getPropertyValue('{prop}')"
    )
    return float(value.removesuffix("px"))


def test_ui_041_main_screen_at_1080p_is_dark_big_and_takes_turns(
    browser: Browser, live_server, tmp_path
):
    context = browser.new_context(viewport=HD, ignore_https_errors=True)
    page = context.new_page()
    errors = _errors(page)
    try:
        page.goto(_url(live_server))
        expect(page.get_by_role("heading", name="Top players")).to_be_visible()
        # UI-042: the dark screen background. UI-041: no text below the config size at 1080p.
        background = page.locator("body").evaluate(
            "e => getComputedStyle(e).backgroundColor"
        )
        assert background == "rgb(14, 16, 21)"  # --color-screen-bg
        for selector in (".screen-brand", ".screen-title", ".screen-note"):
            assert (
                _px(page, selector, "font-size")
                >= CFG["main_screen"]["min_text_px_1080p"]
            )
        page.screenshot(path=tmp_path / "screen-1080.png")
        # API-031: the next view comes in by itself after one turn.
        turn_ms = (CFG["main_screen"]["rotate_seconds"] + 5) * 1000
        expect(page.get_by_role("heading", name="Top churches")).to_be_visible(
            timeout=turn_ms
        )
        assert errors == []
    finally:
        context.close()


def test_ui_002_main_screen_fits_min_width(page: Page, live_server, tmp_path):
    errors = _errors(page)
    page.goto(_url(live_server))
    expect(page.get_by_role("heading", name="Top players")).to_be_visible()
    width = CFG["ui"]["min_viewport_px"]
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    page.screenshot(path=tmp_path / "screen-360.png", full_page=True)
    assert errors == []


def test_ui_040_off_game_shows_offline(page: Page, live_server, test_db_path, tmp_path):
    _set(test_db_path, "off")
    page.goto(_url(live_server))
    expect(page.get_by_role("heading", name="Side Quest is offline")).to_be_visible()
    page.screenshot(path=tmp_path / "screen-off.png", full_page=True)


def test_arch_037_wrong_key_looks_like_any_unknown_page(page: Page, live_server):
    # API-021: the same not found page as a made-up link, so the key page can't be told apart.
    response = page.goto(f"{live_server}/screen?{screen_key.PARAM}=test-only-wrong")
    assert response.status == 404
    wrong_key = page.content()
    page.goto(f"{live_server}/test-only-no-such-page")
    assert page.content() == wrong_key


def test_ui_044_admin_panel_at_min_width(
    page: Page, live_server, test_db_path, browser_name, tmp_path
):
    # Each browser gets its own admin, since usernames are unique (ARCH-036).
    username = f"test-admin-screen-{browser_name}"
    conn = connect(test_db_path)
    create_account(conn, username, FAKE_PASSWORD, "admin")
    conn.close()
    errors = _errors(page)

    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/admin")
    panel = page.locator("#main-screen")
    try:
        expect(panel.get_by_role("link")).to_have_attribute(
            "href", f"{live_server}/screen?{screen_key.PARAM}={FAKE_SCREEN_KEY}"
        )
        expect(panel.locator("strong")).to_have_text("the offline message")
        width = CFG["ui"]["min_viewport_px"]
        assert page.evaluate("document.documentElement.scrollWidth") <= width
        page.screenshot(path=tmp_path / "admin-main-screen.png", full_page=True)

        # Recap swaps the panel in place: the marker set before the click survives (no reload).
        page.evaluate("window.noReload = true")
        panel.get_by_role("button", name="Recap").click()
        expect(page.locator("#main-screen strong")).to_have_text("the recap")
        assert page.evaluate("window.noReload") is True
        expect(page.get_by_role("button", name="Recap")).to_be_disabled()
        assert errors == []
    finally:
        conn = connect(test_db_path)
        conn.execute("UPDATE game_state SET screen_off_view = 'offline'")
        conn.commit()
        conn.close()
