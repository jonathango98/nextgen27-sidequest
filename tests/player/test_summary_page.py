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
