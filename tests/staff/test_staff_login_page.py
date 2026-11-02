import re

from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services.staff import create_account

FAKE_PASSWORD = "test password only 1"  # fake data (ENG-047)


def _account(test_db_path, role, browser_name):
    # Each browser gets its own accounts, since usernames are unique (ARCH-036).
    username = f"test-{role}-{browser_name}"
    conn = connect(test_db_path)
    create_account(conn, username, FAKE_PASSWORD, role)
    conn.close()
    return username


def _log_in(page: Page, live_server, username):
    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def test_arch_035_staff_login_at_min_width(
    page: Page, live_server, test_db_path, browser_name
):
    admin = _account(test_db_path, "admin", browser_name)
    usher = _account(test_db_path, "usher", browser_name)
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    # Logged out: a staff page sends you to log in.
    page.goto(f"{live_server}/admin")
    page.wait_for_url(f"{live_server}/staff/login")
    expect(page.get_by_role("heading", name="Staff log in")).to_be_visible()
    _fits(page)

    # A wrong password stays on the form with a message, and the password field is empty.
    page.get_by_label("Username").fill(admin)
    page.get_by_label("Password").fill("wrong password")
    page.get_by_role("button", name="Log in").click()
    expect(page.locator('[data-error-code="BAD_INPUT"]')).to_be_visible()
    expect(page.get_by_label("Password")).to_have_value("")

    # Admin lands on the admin console, and can open the usher console too (DEC-063).
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/admin")
    expect(page.get_by_role("heading", name="Admin console")).to_be_visible()
    _fits(page)
    page.get_by_role("link", name="Usher console").click()
    page.wait_for_url(f"{live_server}/usher")
    expect(page.get_by_role("heading", name="Usher console")).to_be_visible()

    # Log out goes back to the staff login.
    page.get_by_role("button", name="Log out").click()
    page.wait_for_url(f"{live_server}/staff/login")

    # Usher lands on the usher console and is turned away from the admin one.
    _log_in(page, live_server, usher)
    page.wait_for_url(f"{live_server}/usher")
    page.goto(f"{live_server}/admin")
    expect(page.locator('[data-error-code="WRONG_ROLE"]')).to_be_visible()
    _fits(page)

    # The browser logs the 400 (wrong password) and 403 (WRONG_ROLE) this test asks for on purpose,
    # and htmx logs the 400 it swaps in as an error (API-006). Anything else is a real console
    # error (ENG-045).
    expected = re.compile(
        r"status of (400|403) |^Response Status Error Code 400 from /staff/login"
    )
    assert [e for e in errors if not expected.search(e)] == []
