from playwright.sync_api import Page, expect

from app.config import load_config

ACTIONS = ("Meet friends", "Write", "Read", "Claim box")


def _action(page: Page, name: str):
    nav = page.get_by_role("navigation", name="Things to do")
    return nav.get_by_role("link", name=name)


def test_ui_036_home_shows_big_score_then_box_progress(
    page: Page, live_server, fake_score
):
    page.goto(f"{live_server}/")
    heading = page.get_by_role("heading", level=1)
    expect(heading).to_have_text(f"{fake_score} points")
    milestone = load_config()["blind_box"]["milestone_points"]
    bar = page.get_by_role("progressbar", name="Points toward your next blind box")
    expect(bar).to_have_attribute("aria-valuemax", str(milestone))
    expect(page.locator(".progress-label")).to_contain_text(f"/ {milestone}")
    assert bar.bounding_box()["y"] > heading.bounding_box()["y"]


def test_ui_003_home_actions_sit_in_the_lower_half(page: Page, live_server):
    page.goto(f"{live_server}/")
    half = page.viewport_size["height"] / 2
    tap_min = load_config()["ui"]["min_tap_target_px"]
    for name in ACTIONS:
        box = _action(page, name).bounding_box()
        assert box["y"] >= half, name
        assert box["height"] >= tap_min, name


def test_ui_036_home_actions_are_in_order(page: Page, live_server):
    page.goto(f"{live_server}/")
    meet, write, read, box = (_action(page, n).bounding_box() for n in ACTIONS)
    # Meet friends, then Write and Read side by side, then Claim box (DEC-062).
    assert meet["y"] < write["y"] < box["y"]
    assert write["y"] == read["y"] and write["x"] < read["x"]


def test_ui_035_meet_friends_is_the_only_black_button(page: Page, live_server):
    page.goto(f"{live_server}/")
    for name in ACTIONS:
        color = _action(page, name).evaluate(
            "(el) => getComputedStyle(el).backgroundColor"
        )
        assert (color == "rgb(0, 0, 0)") == (name == "Meet friends"), name


def test_ui_008_home_score_sits_on_a_pear_panel(page: Page, live_server):
    page.goto(f"{live_server}/")
    accent = page.evaluate(
        "(() => { const probe = document.createElement('span');"
        " probe.style.color = 'var(--color-accent)'; document.body.append(probe);"
        " const c = getComputedStyle(probe).color; probe.remove(); return c; })()"
    )
    panel = page.locator(".home-score")
    assert panel.evaluate("(el) => getComputedStyle(el).backgroundColor") == accent
    # The halftone blob is decoration only: drawn by CSS, never catching a tap.
    blob = panel.evaluate("(el) => getComputedStyle(el, '::before').pointerEvents")
    assert blob == "none"
    standing = page.locator(".standing")
    if standing.count():
        color = standing.evaluate("(el) => getComputedStyle(el).backgroundColor")
        assert color == "rgb(0, 0, 0)"


def test_ui_008_home_has_no_viewfinder_corners(page: Page, live_server):
    page.goto(f"{live_server}/")
    corner = page.locator(".top-bar").evaluate(
        "(el) => getComputedStyle(el, '::before').borderTopStyle"
    )
    assert corner != "solid"


def test_ui_002_home_fits_and_has_no_errors(page: Page, live_server):
    problems = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.goto(f"{live_server}/")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]
    assert problems == []
