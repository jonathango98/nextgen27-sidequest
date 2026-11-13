from playwright.sync_api import Page, expect

from app.config import load_config

PAGE = "/_test/components"


def _style(locator, prop):
    return locator.evaluate(f"(el) => getComputedStyle(el).{prop}")


def _token_px(page: Page, name: str) -> float:
    value = page.evaluate(
        "(name) => getComputedStyle(document.documentElement).getPropertyValue(name)",
        name,
    )
    return float(value.strip().removesuffix("px"))


def test_ui_035_one_main_button_and_the_rest_outlined(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    main = page.locator(".button:not(.button-secondary)")
    expect(main).to_have_count(1)
    assert _style(main, "backgroundColor") == "rgb(0, 0, 0)"
    assert _style(main, "color") == "rgb(255, 255, 255)"
    assert _style(main, "backgroundImage") == "none"
    secondary = page.locator(".button-secondary")
    for i in range(secondary.count()):
        button = secondary.nth(i)
        assert _style(button, "backgroundColor") == "rgb(255, 255, 255)"
        # 1.5px, which a 1x screen draws as 1px
        assert float(_style(button, "borderTopWidth").removesuffix("px")) >= 1
        assert _style(button, "borderTopColor") == "rgb(0, 0, 0)"
        assert _style(button, "backgroundImage") == "none"


def test_ui_008_nothing_is_glass_or_shadowed(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    flat = page.evaluate(
        """() => [...document.querySelectorAll('*')].filter((el) => {
            const s = getComputedStyle(el);
            return (s.boxShadow !== 'none' && !el.closest('.top-bar'))
                || (s.backdropFilter && s.backdropFilter !== 'none')
                || s.backgroundImage.includes('gradient');
        }).map((el) => el.tagName)"""
    )
    assert flat == []


def test_ui_008_every_button_is_a_pill(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    pill = _token_px(page, "--radius-pill")
    buttons = page.locator(".button")
    for i in range(buttons.count()):
        radius = float(_style(buttons.nth(i), "borderTopLeftRadius").removesuffix("px"))
        assert radius >= pill / 2 or radius >= 30, i


def test_ui_003_buttons_are_big_enough_to_tap(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    tap_min = load_config()["ui"]["min_tap_target_px"]
    buttons = page.locator(".button")
    for i in range(buttons.count()):
        assert buttons.nth(i).bounding_box()["height"] >= tap_min


def test_ui_008_buttons_use_the_display_font(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    display = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--font-family-display')"
    )
    expected = display.strip().split(",")[0].strip('"')
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


def test_ui_008_points_pill_is_pear(page: Page, live_server):
    page.goto(f"{live_server}{PAGE}")
    points = load_config()["points"]["journal_takeaway"]
    pill = page.locator(".pill")
    expect(pill).to_have_text(f"+{points}")
    accent = page.evaluate(
        "(() => { const probe = document.createElement('span');"
        " probe.style.color = 'var(--color-accent)'; document.body.append(probe);"
        " const c = getComputedStyle(probe).color; probe.remove(); return c; })()"
    )
    assert _style(pill, "backgroundColor") == accent
    # Black text on Pear, never white (UI-008).
    assert _style(pill, "color") == "rgb(0, 0, 0)"


def test_ui_002_components_page_fits_and_has_no_errors(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    response = page.goto(f"{live_server}{PAGE}")
    assert response.status == 200
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]
    assert problems == []
