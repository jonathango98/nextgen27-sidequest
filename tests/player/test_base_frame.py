from playwright.sync_api import Page, expect

from app.config import load_config
from app.main import templates

BUTTONS = ("Home", "My Code", "Quests")


def test_arch_001_template_autoescapes_html():
    html = templates.get_template("player/base.html").render(score="<script>x</script>")
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_ui_030_frame_shows_score_and_three_buttons(
    page: Page, live_server, fake_score
):
    page.goto(f"{live_server}/_test/frame")
    expect(page.locator(".score")).to_have_text(str(fake_score))
    expect(page.get_by_text("points")).to_be_visible()
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
