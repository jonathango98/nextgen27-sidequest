from playwright.sync_api import Page, expect

from app.config import load_config


def test_ui_035_switched_off_submit_is_frosted_not_black(page: Page, live_server):
    page.goto(f"{live_server}/journal/new")
    save = page.get_by_role("button", name="Submit")
    expect(save).to_be_disabled()
    style = save.evaluate(
        "(el) => { const s = getComputedStyle(el);"
        " return {image: s.backgroundImage, color: s.backgroundColor}; }"
    )
    assert style["image"] == "none"
    assert style["color"].startswith("rgba(255, 255, 255")


def test_game_031_journal_fields_sit_on_a_card_with_submit_below(
    page: Page, live_server
):
    page.goto(f"{live_server}/journal/new")
    card = page.locator(".journal-form .card")
    # UI-053, DEC-062: the page title labels the text box.
    expect(card.get_by_role("textbox", name="Journal")).to_be_visible()
    for choice in ("Just me", "With name", "Anonymous"):
        expect(card.get_by_label(choice)).to_be_visible()
    save = page.get_by_role("button", name="Submit").bounding_box()
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


def test_ui_039_cancel_sits_under_submit_and_goes_home(page: Page, live_server):
    page.goto(f"{live_server}/journal/new")
    save = page.get_by_role("button", name="Submit").bounding_box()
    cancel = page.get_by_role("link", name="Cancel")
    assert cancel.bounding_box()["y"] >= save["y"] + save["height"]
    cancel.click()
    expect(page).to_have_url(f"{live_server}/")


def test_game_031_journal_list_fits_and_back_goes_home(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.goto(f"{live_server}/journal")
    back = page.get_by_role("link", name="Back to home")
    title = page.get_by_role("heading", level=1)
    write = page.get_by_role("link", name="Write a takeaway")
    assert (
        back.bounding_box()["y"] < title.bounding_box()["y"] < write.bounding_box()["y"]
    )
    width = load_config()["ui"]["min_viewport_px"]
    cards = page.locator(".takeaway-card")
    for i in range(cards.count()):
        box = cards.nth(i).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    assert problems == []
    back.click()
    expect(page).to_have_url(f"{live_server}/")


def test_ui_053_journal_text_box_is_named_by_the_title(page: Page, live_server):
    page.goto(f"{live_server}/journal/new")
    box = page.get_by_role("textbox")
    expect(box).to_have_accessible_name("Journal Example Session 1")
    expect(page.get_by_text("Takeaway", exact=True)).to_have_count(0)
