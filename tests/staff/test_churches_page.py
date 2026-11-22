from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services.staff import create_account

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def test_safe_002_admin_adds_and_renames_a_church_at_min_width(
    page: Page, live_server, test_db_path, browser_name, tmp_path
):
    # The test server's database is shared, so each browser gets its own admin and church.
    admin = f"test-admin-churches-{browser_name}"
    church = f"Example Church D {browser_name}"
    renamed = f"Example Church E {browser_name}"
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

    # GAME-110: the Churches tile on the admin console.
    page.get_by_role("link", name="Churches").click()
    page.wait_for_url(f"{live_server}/admin/churches")

    # SAFE-002: add a church.
    page.get_by_text("Add", exact=True).click()
    page.locator("#add-name").fill(church)
    _fits(page)
    page.screenshot(path=tmp_path / "churches-adding.png", full_page=True)
    page.get_by_role("button", name="Add church").click()
    card = page.locator("article", has=page.get_by_role("heading", name=church))
    expect(card).to_be_visible()
    _fits(page)
    page.screenshot(path=tmp_path / "churches-added.png", full_page=True)

    # A look-alike name is refused, says why (UI-051), and keeps what was typed.
    page.get_by_text("Add", exact=True).click()
    page.locator("#add-name").fill(church.upper())
    page.get_by_role("button", name="Add church").click()
    expect(page.get_by_role("alert")).to_contain_text("already in the list")
    expect(page.locator("#add-name")).to_have_value(church.upper())
    _fits(page)
    page.screenshot(path=tmp_path / "churches-error.png", full_page=True)

    # GAME-018: rename keeps the church. The new name shows at sign-up.
    page.goto(f"{live_server}/admin/churches")
    card.get_by_text("Rename").click()
    card.get_by_label("New name").fill(renamed)
    _fits(page)
    page.screenshot(path=tmp_path / "churches-renaming.png", full_page=True)
    card.get_by_role("button", name="Save").click()
    expect(
        page.locator("article", has=page.get_by_role("heading", name=renamed))
    ).to_be_visible()
    page.goto(f"{live_server}/join")
    expect(page.locator("option", has_text=renamed)).to_have_count(1)
    expect(page.locator("option", has_text=church)).to_have_count(0)

    # The browser logs the 400 from the refused form this test asks for on purpose. Anything else
    # is a real console error (ENG-045).
    assert [e for e in errors if "status of 400 " not in e] == []
    assert len(errors) <= 1
