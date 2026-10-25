from playwright.sync_api import Page, expect

from app.config import load_config

REFRESH_TIMEOUT_MS = 5000  # test wait, not a game number


def test_game_001_my_code_shows_large_qr(page: Page, live_server):
    page.goto(f"{live_server}/code")
    panel = page.locator(".qr-panel svg")
    expect(panel).to_be_visible()
    content_width = page.evaluate("document.querySelector('.content').clientWidth")
    assert panel.bounding_box()["width"] >= content_width / 2
    expect(page.get_by_text("brightness")).to_be_visible()


def test_api_030_my_code_swaps_in_new_code(page: Page, live_server):
    page.goto(f"{live_server}/code")
    path = page.locator(".qr-panel svg path")
    first = path.get_attribute("d")
    expect(path).not_to_have_attribute("d", first, timeout=REFRESH_TIMEOUT_MS)


def test_ui_002_my_code_has_no_sideways_scroll(page: Page, live_server):
    page.goto(f"{live_server}/code")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]


def test_eng_045_my_code_has_no_console_errors(page: Page, live_server):
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{live_server}/code")
    page.wait_for_load_state("networkidle")
    assert errors == []


def test_dec_031_my_code_retries_after_failed_refresh(page: Page, live_server):
    failures = []

    def fail_once(route):
        if not failures:
            failures.append(route.request.url)
            route.abort()
        else:
            route.continue_()

    page.route("**/code/qr", fail_once)
    page.goto(f"{live_server}/code")
    path = page.locator(".qr-panel svg path")
    first = path.get_attribute("d")
    retry_ms = load_config()["qr"]["poll_retry_seconds"] * 1000
    expect(path).not_to_have_attribute(
        "d", first, timeout=REFRESH_TIMEOUT_MS + retry_ms
    )
    assert len(failures) == 1


def test_api_006_my_code_shows_error_partial(page: Page, live_server):
    page.route(
        "**/code/qr",
        lambda route: route.fulfill(
            status=401,
            content_type="text/html",
            body='<p role="alert" data-error-code="LOGIN_REQUIRED">Please log in first.</p>',
        ),
    )
    page.goto(f"{live_server}/code")
    expect(page.locator('[data-error-code="LOGIN_REQUIRED"]')).to_be_visible(
        timeout=REFRESH_TIMEOUT_MS
    )


def test_ui_030_my_code_tab_is_current(page: Page, live_server):
    page.goto(f"{live_server}/code")
    nav = page.get_by_role("navigation", name="Main")
    expect(nav.get_by_role("link", name="My Code")).to_have_attribute(
        "aria-current", "page"
    )
    for name in ("Home", "Quests"):
        expect(nav.get_by_role("link", name=name)).not_to_have_attribute(
            "aria-current", "page"
        )


def test_ui_030_my_code_has_scan_button(page: Page, live_server):
    page.goto(f"{live_server}/code")
    scan = page.get_by_role("main").get_by_role("link", name="Scan")
    expect(scan).to_have_attribute("href", "/scan")
    tap_min = load_config()["ui"]["min_tap_target_px"]
    assert scan.bounding_box()["height"] >= tap_min  # UI-003
