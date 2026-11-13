import re

import pytest
from playwright.sync_api import Page, expect

from app.config import load_config
from app.main import templates
from app.services import blind_boxes

BUTTONS = ("Home", "My Code", "Quests")


def test_arch_001_template_autoescapes_html():
    cfg = load_config()
    html = templates.get_template("player/home.html").render(
        score="<script>x</script>",
        # The rest of what the Home route passes (UI-036), from game-config.yaml (AI-013).
        journal_points=cfg["points"]["journal_takeaway"],
        box=blind_boxes.progress(0, cfg["blind_box"]),
    )
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_ui_030_frame_shows_just_the_name_and_three_buttons(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    top_bar = page.locator(".top-bar")
    expect(top_bar).to_have_text("Side Quest")
    expect(top_bar.get_by_role("link", name="Side Quest")).to_have_attribute(
        "href", "/"
    )
    nav = page.get_by_role("navigation", name="Main")
    for name in BUTTONS:
        expect(nav.get_by_role("link", name=name)).to_be_visible()


def test_ui_002_frame_has_no_sideways_scroll(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]


def test_ui_003_bottom_buttons_are_big_and_in_lower_half(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    tap_min = load_config()["ui"]["min_tap_target_px"]
    half = page.viewport_size["height"] / 2
    nav = page.get_by_role("navigation", name="Main")
    for name in BUTTONS:
        box = nav.get_by_role("link", name=name).bounding_box()
        assert box["width"] >= tap_min and box["height"] >= tap_min, name
        assert box["y"] >= half, name


def test_ui_030_frame_has_no_console_errors(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    response = page.goto(f"{live_server}/_test/frame")
    expect(page.get_by_role("navigation", name="Main")).to_be_visible()
    assert response.status == 200
    assert problems == []


def test_ui_008_page_is_flat_with_no_background_layers(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    # The Mix streaks and grain are gone: the page is plain white (UI-008, DEC-080).
    for pseudo in ("::before", "::after"):
        content = page.evaluate(
            "(p) => getComputedStyle(document.body, p).content", pseudo
        )
        assert content in ("none", "normal")
    assert _style(page, "body", "backgroundColor") == "rgb(255, 255, 255)"
    assert _style(page, "body", "backgroundImage") == "none"


def test_ui_008_top_bar_is_black_with_the_k_mark(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    bar = page.locator(".top-bar")
    assert _style(page, ".top-bar", "backgroundColor") == "rgb(0, 0, 0)"
    mark = bar.locator("img")
    expect(mark).to_have_attribute("src", re.compile(r"/img/k-mark-white\.webp"))
    expect(mark).to_have_attribute("alt", "")
    expect(bar.locator(".top-bar-halftone")).to_have_attribute("aria-hidden", "true")
    height = float(_token(page, "--topbar-height").removesuffix("px"))
    assert bar.bounding_box()["height"] == height
    assert mark.evaluate("(el) => el.complete && el.naturalWidth > 0")


def test_ui_004_display_font_is_preloaded(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    link = page.locator('link[rel="preload"][as="font"]')
    expect(link).to_have_attribute("href", "/static/fonts/outfit-latin.woff2")
    expect(link).to_have_attribute("crossorigin", "")


def test_ui_008_tab_icon_is_the_k_mark(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    for rel in ("icon", "apple-touch-icon"):
        href = page.locator(f'link[rel="{rel}"]').get_attribute("href")
        assert href.startswith("/static/img/")
        assert page.request.get(f"{live_server}{href}").ok


def _style(page: Page, selector: str, prop: str):
    return page.locator(selector).first.evaluate(f"(el) => getComputedStyle(el).{prop}")


def _token(page: Page, name: str):
    return page.evaluate(
        "(name) => getComputedStyle(document.documentElement).getPropertyValue(name)",
        name,
    ).strip()


def test_ui_030_each_tab_has_icon_and_label(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    nav = page.get_by_role("navigation", name="Main")
    tab_min = float(_token(page, "--tab-min").removesuffix("px"))
    for name in BUTTONS:
        tab = nav.get_by_role("link", name=name, exact=True)
        expect(tab.locator('svg[aria-hidden="true"]')).to_have_count(1)
        assert tab.bounding_box()["height"] >= tab_min, name


def test_ui_030_only_current_tab_has_the_pear_pill(page: Page, live_server):
    page.goto(f"{live_server}/quests")
    nav = page.get_by_role("navigation", name="Main")
    accent = page.evaluate(
        "(() => { const probe = document.createElement('span');"
        " probe.style.color = 'var(--color-accent)'; document.body.append(probe);"
        " const c = getComputedStyle(probe).color; probe.remove(); return c; })()"
    )
    for name in BUTTONS:
        pill = nav.get_by_role("link", name=name, exact=True).locator(".tab-icon")
        color = pill.evaluate("(el) => getComputedStyle(el).backgroundColor")
        assert (color == accent) == (name == "Quests"), name


def test_ui_008_titles_and_buttons_use_the_display_font(page: Page, live_server):
    page.goto(f"{live_server}/quests")
    display = _token(page, "--font-family-display").split(",")[0].strip('"')
    for element in (
        page.locator("h1"),
        page.locator(".top-bar").get_by_role("link", name="Side Quest"),
    ):
        font = element.evaluate("(el) => getComputedStyle(el).fontFamily")
        assert font.startswith(display), font


@pytest.mark.parametrize(
    "path", ["/quests", "/code", "/journal", "/summary", "/box", "/scan", "/join"]
)
def test_ui_058_page_titles_are_lowercase_and_end_with_a_period(
    page: Page, live_server, path
):
    page.goto(f"{live_server}{path}")
    title = page.get_by_role("heading", level=1).first.inner_text().strip()
    assert title == title.lower(), title
    assert title.endswith("."), title


def test_ui_030_scan_is_not_a_tab(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    nav = page.get_by_role("navigation", name="Main")
    expect(nav.get_by_role("link", name="Scan")).to_have_count(0)


def test_ui_030_top_bar_links_home(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    link = page.locator(".top-bar").get_by_role("link", name="Side Quest")
    expect(link).to_have_attribute("href", "/")
    tap_min = load_config()["ui"]["min_tap_target_px"]
    assert link.bounding_box()["height"] >= tap_min
