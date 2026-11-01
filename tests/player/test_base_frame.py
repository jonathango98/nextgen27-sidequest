from playwright.sync_api import Page, expect

from app.config import load_config
from app.main import templates

BUTTONS = ("Home", "My Code", "Quests")


def test_arch_001_template_autoescapes_html():
    html = templates.get_template("player/home.html").render(score="<script>x</script>")
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


def _layer_style(page: Page, pseudo: str):
    return page.evaluate(
        """(pseudo) => {
            const s = getComputedStyle(document.body, pseudo);
            return {position: s.position, pointerEvents: s.pointerEvents,
                    zIndex: s.zIndex, image: s.backgroundImage};
        }""",
        pseudo,
    )


def test_ui_008_background_is_decoration_only(page: Page, live_server):
    page.goto(f"{live_server}/_test/frame")
    streaks = _layer_style(page, "::before")
    grain = _layer_style(page, "::after")
    # Drawn by CSS behind the page, so it never catches a tap or reaches a screen reader.
    for layer in (streaks, grain):
        assert layer["position"] == "fixed"
        assert layer["pointerEvents"] == "none"
        assert layer["zIndex"] == "-1"
    assert "radial-gradient" in streaks["image"]
    assert "data:image/svg+xml" in grain["image"]


def test_dec_036_background_downloads_no_image_file(page: Page, live_server):
    images = []
    page.on(
        "request",
        lambda r: images.append(r.url) if r.resource_type == "image" else None,
    )
    page.goto(f"{live_server}/_test/frame")
    page.wait_for_load_state("networkidle")
    assert [url for url in images if not url.startswith("data:")] == []


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


def test_ui_030_only_current_tab_is_filled(page: Page, live_server):
    page.goto(f"{live_server}/quests")
    nav = page.get_by_role("navigation", name="Main")
    for name in BUTTONS:
        image = nav.get_by_role("link", name=name, exact=True).evaluate(
            "(el) => getComputedStyle(el).backgroundImage"
        )
        assert ("gradient" in image) == (name == "Quests"), name


def test_ui_008_titles_and_name_use_the_serif(page: Page, live_server):
    page.goto(f"{live_server}/quests")
    serif = _token(page, "--font-family-display").split(",")[0]
    for element in (
        page.locator("h1"),
        page.locator(".top-bar").get_by_role("link", name="Side Quest"),
    ):
        font = element.evaluate("(el) => getComputedStyle(el).fontFamily")
        assert font.startswith(serif), font


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
