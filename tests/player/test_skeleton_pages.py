import pytest
from playwright.sync_api import Page, expect

from app.config import load_config

PAGES = (
    "/",
    "/scan",
    "/connections/1",
    "/quests",
    "/journal",
    "/journal/new",
    "/summary",
    "/box",
    "/wrapped",
)


@pytest.mark.parametrize("path", PAGES)
def test_eng_045_skeleton_page_works_at_360px(page: Page, live_server, path):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    response = page.goto(f"{live_server}{path}")
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    assert response.status == 200
    assert problems == []
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]


def test_ui_036_meet_friends_opens_scanner(page: Page, live_server):
    page.goto(f"{live_server}/")
    page.get_by_role("link", name="Meet friends").click()
    expect(page).to_have_url(f"{live_server}/scan")
    nav = page.get_by_role("navigation", name="Main")
    expect(nav.get_by_role("link", name="My Code")).to_have_attribute(
        "aria-current", "page"
    )


def test_ui_037_scan_button_opens_scanner(page: Page, live_server):
    page.goto(f"{live_server}/code")
    page.get_by_role("link", name="Scan").click()
    expect(page).to_have_url(f"{live_server}/scan")
