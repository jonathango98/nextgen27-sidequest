from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services.game_state import set_state
from app.services.staff import create_account

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def _set(test_db_path, state):
    conn = connect(test_db_path)
    try:
        set_state(conn, state)
    finally:
        conn.close()


def test_game_026_admin_adds_edits_and_ends_a_session_at_min_width(
    page: Page, live_server, test_db_path, browser_name, tmp_path
):
    # The test server's database is shared, so each browser gets its own admin and session.
    username = f"test-admin-sessions-{browser_name}"
    title = f"Example Session 1 {browser_name}"
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
    try:
        _fits(page)
        page.screenshot(path=tmp_path / "admin-console.png", full_page=True)
        page.get_by_role("link", name="Sessions").click()
        page.wait_for_url(f"{live_server}/admin/sessions")
        # GAME-107, OPS-001: says the timetable pause is only a backup.
        expect(
            page.get_by_text("This is only a backup: still press Pause.")
        ).to_be_visible()
        _fits(page)
        page.screenshot(path=tmp_path / "sessions-empty.png", full_page=True)

        # Add, with a start time and check-in minutes (DATA-014, GAME-021).
        page.locator("#add-title").fill(title)
        page.locator("#add-starts-at").fill("2027-03-06T09:30")
        page.locator("#add-minutes").fill("15")
        page.get_by_role("button", name="Add session").click()
        card = page.locator("article", has=page.get_by_role("heading", name=title))
        expect(card).to_contain_text("Starts Sat Mar 6, 9:30 AM")
        expect(card).to_contain_text("Check-in opens 15 min before.")
        page.reload()
        expect(card).to_be_visible()
        _fits(page)
        page.screenshot(path=tmp_path / "sessions-added.png", full_page=True)

        # Edit the title in place.
        card.get_by_text("Edit").click()
        card.get_by_label("Title").fill(f"{title}b")
        _fits(page)
        page.screenshot(path=tmp_path / "sessions-editing.png", full_page=True)
        card.get_by_role("button", name="Save").click()
        title = f"{title}b"
        card = page.locator("article", has=page.get_by_role("heading", name=title))
        expect(card).to_be_visible()

        # A refused form says why, in text (UI-051).
        page.locator("#add-title").fill("Example Session 9")
        page.locator("#add-starts-at").fill("2027-03-06T13:00")
        page.get_by_role("button", name="Add session").click()
        expect(page.get_by_role("alert")).to_contain_text("how many minutes")
        expect(page.locator("#add-title")).to_have_value("Example Session 9")
        _fits(page)
        page.screenshot(path=tmp_path / "sessions-error.png", full_page=True)

        # End session while paused: asks first, turns the game on, opens takeaways (GAME-026).
        _set(test_db_path, "paused")
        page.goto(f"{live_server}/admin/sessions")
        expect(page.locator("[data-state]")).to_have_text("Paused")
        page.evaluate("window.noReload = true")
        page.once("dialog", lambda dialog: dialog.accept())
        card.get_by_role("button", name="End session").click()
        expect(page.get_by_role("status")).to_contain_text("The game is on again")
        expect(page.locator("[data-state]")).to_have_text("On")
        expect(card).to_contain_text("Ended.")
        assert page.evaluate("window.noReload === true")  # HTMX swapped the list
        _fits(page)
        page.screenshot(path=tmp_path / "sessions-ended.png", full_page=True)

        # Pressing it again changes nothing and says so.
        page.once("dialog", lambda dialog: dialog.accept())
        card.get_by_role("button", name="End session").click()
        expect(page.get_by_role("status")).to_contain_text("Nothing changed.")
        expect(page.locator("[data-state]")).to_have_text("On")
        page.screenshot(path=tmp_path / "sessions-ended-again.png", full_page=True)
    finally:
        _set(test_db_path, "on")

    # The browser logs the 400 from the refused form this test asks for on purpose. Anything else
    # is a real console error (ENG-045).
    assert [e for e in errors if "status of 400 " not in e] == []
    assert len(errors) <= 1
