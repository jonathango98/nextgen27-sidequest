from playwright.sync_api import Page, expect

from app.config import load_config


def test_ui_038_summary_cards_fit_and_wrap(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.goto(f"{live_server}/summary")
    width = load_config()["ui"]["min_viewport_px"]
    cards = page.locator(".takeaway-card")
    expect(cards.first).to_be_visible()
    for i in range(cards.count()):
        box = cards.nth(i).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    assert problems == []


def test_ui_038_summary_cards_are_frosted_glass(page: Page, live_server):
    page.goto(f"{live_server}/summary")
    card = page.locator(".takeaway-card").first
    color = card.evaluate("(el) => getComputedStyle(el).backgroundColor")
    assert color.startswith("rgba(255, 255, 255")


def test_ui_030_back_to_home_sits_above_the_title_and_goes_home(
    page: Page, live_server
):
    page.goto(f"{live_server}/summary")
    back = page.get_by_role("link", name="Back to home")
    title = page.get_by_role("heading", level=1)
    assert back.bounding_box()["y"] < title.bounding_box()["y"]
    assert back.bounding_box()["height"] >= load_config()["ui"]["min_tap_target_px"]
    back.click()
    expect(page).to_have_url(f"{live_server}/")


def test_safe_009_summary_shows_name_and_church_or_anonymous(page: Page, live_server):
    page.goto(f"{live_server}/summary")
    authors = page.locator(".takeaway-author")
    expect(authors.filter(has_text="Anonymous")).not_to_have_count(0)
    expect(authors.filter(has_text="Example Church A")).not_to_have_count(0)
