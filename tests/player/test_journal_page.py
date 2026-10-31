from playwright.sync_api import Page, expect

from app.config import load_config


def test_ui_035_switched_off_save_is_frosted_not_black(page: Page, live_server):
    page.goto(f"{live_server}/journal/new")
    save = page.get_by_role("button", name="Save")
    expect(save).to_be_disabled()
    style = save.evaluate(
        "(el) => { const s = getComputedStyle(el);"
        " return {image: s.backgroundImage, color: s.backgroundColor}; }"
    )
    assert style["image"] == "none"
    assert style["color"].startswith("rgba(255, 255, 255")


def test_game_031_journal_fields_sit_on_a_card_with_save_below(page: Page, live_server):
    page.goto(f"{live_server}/journal/new")
    card = page.locator(".journal-form .card")
    expect(card.get_by_label("Takeaway")).to_be_visible()
    for choice in ("Just me", "With name", "Anonymous"):
        expect(card.get_by_label(choice)).to_be_visible()
    save = page.get_by_role("button", name="Save").bounding_box()
    box = card.bounding_box()
    assert save["y"] >= box["y"] + box["height"]


def test_ui_002_journal_fits_and_has_no_errors(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.goto(f"{live_server}/journal/new")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]
    assert problems == []
