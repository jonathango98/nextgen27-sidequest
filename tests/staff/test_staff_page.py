from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services.staff import create_account

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def test_arch_036_admin_adds_and_switches_off_an_account_at_min_width(
    page: Page, live_server, test_db_path, browser_name, tmp_path
):
    # The test server's database is shared, so each browser gets its own accounts.
    admin = f"test-admin-staff-{browser_name}"
    usher = f"Test Usher {browser_name}"
    conn = connect(test_db_path)
    create_account(conn, admin, FAKE_PASSWORD, "admin")
    conn.close()
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(admin)
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/admin")
    _fits(page)
    page.screenshot(path=tmp_path / "admin-console.png", full_page=True)

    # GAME-110: the Staff tile on the admin console.
    page.get_by_role("link", name="Staff").click()
    page.wait_for_url(f"{live_server}/admin/staff")
    mine = page.locator("article", has=page.get_by_role("heading", name=admin))
    expect(mine).to_contain_text("This is you.")
    expect(mine.get_by_role("button")).to_have_count(0)
    _fits(page)
    page.screenshot(path=tmp_path / "staff-list.png", full_page=True)

    # ARCH-036: add an usher with a password.
    page.get_by_text("Add", exact=True).click()
    page.locator("#add-username").fill(usher)
    page.locator("#add-password").fill(FAKE_PASSWORD)
    _fits(page)
    page.screenshot(path=tmp_path / "staff-adding.png", full_page=True)
    page.get_by_role("button", name="Add account").click()
    card = page.locator("article", has=page.get_by_role("heading", name=usher))
    expect(card).to_contain_text("Usher")

    # A refused add says why (UI-051), keeps the username, and never the password.
    page.get_by_text("Add", exact=True).click()
    page.locator("#add-username").fill(usher.lower())
    page.locator("#add-password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Add account").click()
    expect(page.get_by_role("alert")).to_contain_text("already an account")
    expect(page.locator("#add-username")).to_have_value(usher.lower())
    expect(page.locator("#add-password")).to_have_value("")
    _fits(page)
    page.screenshot(path=tmp_path / "staff-error.png", full_page=True)

    # OPS-042: switch off asks first, and HTMX swaps the list without a reload.
    page.goto(f"{live_server}/admin/staff")
    page.evaluate("window.noReload = true")
    page.once("dialog", lambda dialog: dialog.accept())
    card.get_by_role("button", name="Switch off").click()
    expect(page.get_by_role("status")).to_contain_text(f"{usher} is switched off")
    expect(card.locator(".chip", has_text="Off")).to_be_visible()
    assert page.evaluate("window.noReload === true")
    _fits(page)
    # A full-page screenshot draws the pinned top bar where the scroll left it, so start at the top.
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=tmp_path / "staff-switched-off.png", full_page=True)

    card.get_by_role("button", name="Switch on").click()
    expect(page.get_by_role("status")).to_contain_text(f"{usher} is switched on")
    expect(card.locator(".chip", has_text="Off")).to_have_count(0)

    # The browser logs the 400 from the refused form this test asks for on purpose. Anything else
    # is a real console error (ENG-045).
    assert [e for e in errors if "status of 400 " not in e] == []
    assert len(errors) <= 1
