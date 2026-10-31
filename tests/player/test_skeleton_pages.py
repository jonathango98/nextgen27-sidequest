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


def test_ui_002_icebreaker_form_stacks_its_fields(page: Page, live_server):
    # A form section stacks label, field, and button. Only Join's Yes and No sit side by side.
    page.goto(f"{live_server}/connections/1")
    label = page.get_by_text("Answer", exact=True).bounding_box()
    field = page.get_by_label("Answer").bounding_box()
    save = page.get_by_role("button", name="Save").bounding_box()
    assert label["y"] < field["y"] < save["y"]
    assert field["x"] <= label["x"] + 1


def test_safe_002_join_yes_and_no_sit_side_by_side(page: Page, live_server):
    page.goto(f"{live_server}/join")
    yes = page.get_by_label("Yes").bounding_box()
    no = page.get_by_label("No").bounding_box()
    assert yes["y"] == no["y"] and yes["x"] < no["x"]
