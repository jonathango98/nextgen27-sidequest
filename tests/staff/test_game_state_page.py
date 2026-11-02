from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services.game_state import BANNERS, set_state
from app.services.staff import create_account

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)
# My Code and Quests are the pages the hand test names, after Home (UI-033).
PLAYER_PAGES = ("/", "/code", "/quests")


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def _set(test_db_path, state):
    conn = connect(test_db_path)
    try:
        set_state(conn, state)
    finally:
        conn.close()


def test_game_101_admin_switches_the_game_at_min_width(
    page: Page, live_server, test_db_path, browser_name, tmp_path
):
    # Each browser gets its own admin, since usernames are unique (ARCH-036).
    username = f"test-admin-game-{browser_name}"
    conn = connect(test_db_path)
    create_account(conn, username, FAKE_PASSWORD, "admin")
    conn.close()
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/admin")
    panel = page.locator("#game-state")
    try:
        expect(panel.locator("strong")).to_have_text("On")
        expect(page.get_by_role("button", name="Start")).to_be_disabled()
        _fits(page)
        page.screenshot(path=tmp_path / "admin-on.png", full_page=True)

        # Pause swaps the panel in place: the marker set before the click survives (no reload).
        page.evaluate("window.noReload = true")
        page.get_by_role("button", name="Pause").click()
        expect(panel.locator("strong")).to_have_text("Paused")
        expect(page.get_by_role("button", name="Pause")).to_be_disabled()
        assert page.evaluate("window.noReload === true")
        _fits(page)
        page.screenshot(path=tmp_path / "admin-paused.png", full_page=True)

        # Every player page shows the short paused note (UI-033).
        for path in PLAYER_PAGES:
            page.goto(f"{live_server}{path}")
            expect(page.get_by_role("status")).to_have_text(BANNERS["paused"])
            _fits(page)
        page.goto(f"{live_server}/")
        page.screenshot(path=tmp_path / "home-paused.png", full_page=True)

        # Start brings the game back, and the note is gone on the next page.
        page.goto(f"{live_server}/admin")
        page.get_by_role("button", name="Start").click()
        expect(panel.locator("strong")).to_have_text("On")
        page.goto(f"{live_server}/")
        expect(page.locator(".game-banner")).to_have_count(0)

        # Off asks first (a wrong tap closes sign-up), then sign-up says it is closed (GAME-108).
        page.goto(f"{live_server}/admin")
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Off").click()
        expect(panel.locator("strong")).to_have_text("Off")
        page.goto(f"{live_server}/join")
        expect(page.get_by_text("Sign-up is closed right now.")).to_be_visible()
        expect(page.get_by_label("First name")).to_have_count(0)
        _fits(page)
        page.screenshot(path=tmp_path / "join-off.png", full_page=True)
        page.goto(f"{live_server}/code")
        expect(page.get_by_role("status")).to_have_text(BANNERS["off"])
        page.screenshot(path=tmp_path / "code-off.png", full_page=True)
    finally:
        # The test server's database is shared with other browser tests, so put the game back on.
        _set(test_db_path, "on")

    assert errors == []  # ENG-045
