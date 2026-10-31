from playwright.sync_api import Page, expect

from app.config import load_config

PAGE = "/_test/components"


def _style(locator, prop):
    return locator.evaluate(f"(el) => getComputedStyle(el).{prop}")


def test_ui_035_one_main_button_and_the_rest_frosted(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    main = page.locator(".button:not(.button-secondary)")
    expect(main).to_have_count(1)
    assert "gradient" in _style(main, "backgroundImage")
    secondary = page.locator(".button-secondary")
    for i in range(secondary.count()):
        button = secondary.nth(i)
        assert _style(button, "backgroundImage") == "none"
        # Frosted glass: see-through white with a blur behind it (07 section 3).
        assert _style(button, "backgroundColor").startswith("rgba(255, 255, 255")
        blur = button.evaluate(
            "(el) => { const s = getComputedStyle(el);"
            " return s.backdropFilter || s.webkitBackdropFilter; }"
        )
        assert "blur" in blur


def test_ui_003_buttons_are_big_enough_to_tap(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    tap_min = load_config()["ui"]["min_tap_target_px"]
    buttons = page.locator(".button")
    for i in range(buttons.count()):
        assert buttons.nth(i).bounding_box()["height"] >= tap_min


def test_ui_008_buttons_use_the_serif(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    serif = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--font-family-display')"
    )
    expected = serif.strip().split(",")[0]
    buttons = page.locator(".button")
    for i in range(buttons.count()):
        assert _style(buttons.nth(i), "fontFamily").startswith(expected)


def test_ui_035_button_responds_to_a_tap(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    button = page.get_by_role("button", name="Meet friends")
    assert _style(button, "transform") == "none"
    button.hover()
    page.mouse.down()
    pressed = _style(button, "transform")
    page.mouse.up()
    assert pressed != "none"


def test_ui_051_progress_bar_shows_its_numbers(page: Page, live_server, fake_score):
    page.goto(f"{live_server}{PAGE}")
    milestone = load_config()["blind_box"]["milestone_points"]
    progress = fake_score % milestone
    bar = page.get_by_role("progressbar", name="Points toward your next blind box")
    expect(bar).to_have_attribute("aria-valuenow", str(progress))
    expect(bar).to_have_attribute("aria-valuemax", str(milestone))
    expect(page.locator(".progress-label")).to_contain_text(f"{progress} / {milestone}")


def test_ui_006_points_pill_is_gold(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    points = load_config()["points"]["journal_takeaway"]
    pill = page.locator(".pill")
    expect(pill).to_have_text(f"+{points}")
    gold = page.evaluate(
        "(() => { const probe = document.createElement('span');"
        " probe.style.color = 'var(--color-gold)'; document.body.append(probe);"
        " const c = getComputedStyle(probe).color; probe.remove(); return c; })()"
    )
    assert _style(pill, "backgroundColor") == gold


def test_ui_002_components_page_fits_and_has_no_errors(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    response = page.goto(f"{live_server}{PAGE}")
    assert response.status == 200
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]
    assert problems == []
