import re

from playwright.sync_api import Page, expect

from app.config import load_config


def test_game_031_journal_fields_sit_on_a_card_with_submit_below(
    page: Page, live_server
):
    page.goto(f"{live_server}/journal/new")
    card = page.locator(".journal-form .card")
    # UI-053, DEC-062: the page title labels the text box.
    expect(card.get_by_role("textbox", name="Journal")).to_be_visible()
    # GAME-036: the ended session is offered, and one session is picked. Matched by value, since
    # staff tests add sessions with similar titles to the shared test database.
    expect(card.locator('input[name="session"][value="pub-s1"]')).to_be_visible()
    expect(card.locator('input[name="session"]:checked')).to_have_count(1)
    # GAME-031: three choices, private picked until the player chooses, with the UI-031 note.
    expect(card.locator('input[name="visibility"]')).to_have_count(3)
    expect(card.get_by_label("Just me")).to_be_checked()
    expect(
        card.get_by_text("Game organizers can still see who wrote it.")
    ).to_be_visible()
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
    expect(box).to_have_accessible_name("Journal What did you learn?")
    expect(page.get_by_text("Takeaway", exact=True)).to_have_count(0)


def test_game_034_word_count_goes_up_as_you_type(page: Page, live_server):
    page.goto(f"{live_server}/journal/new")
    minimum = load_config()["limits"]["journal_min_words"]
    page.get_by_role("textbox").fill("God is good - !")
    expect(page.locator(".word-count")).to_have_text(f"3 / {minimum} words")


def test_game_030_short_note_shows_how_many_more_words_and_keeps_text(
    page: Page, live_server
):
    page.goto(f"{live_server}/journal/new")
    minimum = load_config()["limits"]["journal_min_words"]
    page.get_by_role("textbox").fill(" ".join(["listen"] * (minimum - 1)))
    page.get_by_role("button", name="Submit").click()
    expect(page.get_by_role("alert")).to_have_text("Add 1 more word to save this.")
    expect(page.get_by_role("textbox")).to_have_value(
        " ".join(["listen"] * (minimum - 1))
    )
    # The swapped-in form still counts words (journal.js wires it again).
    page.get_by_role("textbox").fill("God is good")
    expect(page.locator(".word-count")).to_have_text(f"3 / {minimum} words")


def test_dec_076_change_who_can_read_a_note_in_place(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    minimum = load_config()["limits"]["journal_min_words"]
    page.goto(f"{live_server}/journal/new")
    page.get_by_role("textbox").fill(" ".join(["kindness"] * minimum))
    page.get_by_role("button", name="Submit").click()
    expect(page).to_have_url(re.compile(r"/journal\?saved="))
    # The newest note is the first card. Change opens the choices with the UI-031 note.
    card = page.locator(".takeaway-card").first
    expect(card.locator(".note-status")).to_have_text("Just me")
    card.get_by_text("Change", exact=True).click()
    expect(
        card.get_by_text("Game organizers can still see who wrote it.")
    ).to_be_visible()
    card.get_by_label("Shared anonymously").check()
    card.get_by_role("button", name="Save").click()
    # HTMX swaps only this card, so the page stays put.
    card = page.locator(".takeaway-card").first
    expect(card.locator(".note-status")).to_have_text("Shared anonymously")
    expect(card.get_by_role("status")).to_have_text("Saved.")
    expect(page).to_have_url(re.compile(r"/journal\?saved="))
    width = load_config()["ui"]["min_viewport_px"]
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    assert problems == []
