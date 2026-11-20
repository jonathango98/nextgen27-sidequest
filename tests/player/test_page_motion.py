from playwright.sync_api import Page, expect

from app.config import load_config

# The CSS rule each player page carries to opt in to page changes (UI-059).
OPT_IN = "@view-transition"


def _dir(page: Page):
    return page.evaluate("document.documentElement.dataset.dir || null")


def _tap_tab(page: Page, live_server, name, path):
    page.get_by_role("navigation", name="Main").get_by_role("link", name=name).click()
    expect(page).to_have_url(f"{live_server}{path}")


def test_ui_059_player_pages_opt_in_to_page_changes(page: Page, live_server):
    page.goto(f"{live_server}/quests")
    expect(page.locator("html")).to_have_attribute("data-tab", "quests")
    assert OPT_IN in page.content()
    rules = page.locator('script[type="speculationrules"]')
    assert '"eagerness": "conservative"' in rules.text_content()


def test_ui_059_staff_and_error_pages_do_not_move(page: Page, live_server):
    for path in ("/staff/login", "/no-such-page"):
        page.goto(f"{live_server}{path}")
        assert OPT_IN not in page.content(), path
        assert page.locator("html").get_attribute("data-tab") is None, path


def test_ui_059_first_load_does_not_slide(page: Page, live_server):
    page.goto(f"{live_server}/")
    assert _dir(page) is None


def test_ui_059_later_tab_slides_from_the_right_and_back_from_the_left(
    page: Page, live_server
):
    page.goto(f"{live_server}/")
    _tap_tab(page, live_server, "My Code", "/code")
    assert _dir(page) == "fwd"
    _tap_tab(page, live_server, "Home", "/")
    assert _dir(page) == "back"


def test_ui_059_opening_a_page_inside_a_tab_slides_from_the_right(
    page: Page, live_server
):
    page.goto(f"{live_server}/")
    page.goto(f"{live_server}/journal")
    assert _dir(page) == "fwd"
    page.get_by_role("link", name="Back to home").click()
    expect(page).to_have_url(f"{live_server}/")
    assert _dir(page) == "back"


def test_ui_059_list_rows_arrive_one_after_another(page: Page, live_server):
    page.goto(f"{live_server}/")
    _tap_tab(page, live_server, "Quests", "/quests")
    delays = page.locator(".quest-list > li").evaluate_all(
        "rows => rows.slice(0, 3).map(r => parseFloat(getComputedStyle(r).animationDelay))"
    )
    assert len(delays) == 3
    assert delays[0] < delays[1] < delays[2]


def test_ui_002_sliding_in_never_scrolls_sideways(page: Page, live_server):
    page.goto(f"{live_server}/")
    _tap_tab(page, live_server, "My Code", "/code")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]


def test_ui_059_tap_fades_the_old_page_and_back_undoes_it(page: Page, live_server):
    page.goto(f"{live_server}/")
    page.evaluate(
        "document.addEventListener('click', e => e.preventDefault(), {capture: true})"
    )
    page.locator(".bottom-bar").get_by_role("link", name="My Code").click()
    # A prevented click never leaves the page, so it must not fade it.
    assert "leaving" not in page.evaluate("document.documentElement.className")
    page.goto(f"{live_server}/")
    _tap_tab(page, live_server, "My Code", "/code")
    page.go_back()
    expect(page).to_have_url(f"{live_server}/")
    expect(page.locator("html")).not_to_have_class("leaving")


def test_ui_055_reduce_motion_turns_page_changes_off(page: Page, live_server):
    page.emulate_media(reduced_motion="reduce")
    page.goto(f"{live_server}/")
    _tap_tab(page, live_server, "Quests", "/quests")
    names = page.locator(".content > *, .quest-list > li").evaluate_all(
        "els => els.map(e => getComputedStyle(e).animationName)"
    )
    assert names and set(names) == {"none"}
