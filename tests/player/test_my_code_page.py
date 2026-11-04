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
            status=423,
            content_type="text/html",
            body='<p role="alert" data-error-code="PAUSED">The game is paused during the session.</p>',
        ),
    )
    page.goto(f"{live_server}/code")
    expect(page.locator('[data-error-code="PAUSED"]')).to_be_visible(
        timeout=REFRESH_TIMEOUT_MS
    )


def test_dec_061_my_code_goes_to_login_when_logged_out(page: Page, live_server):
    # What the server sends an HTMX request once the session is gone.
    page.route(
        "**/code/qr",
        lambda route: route.fulfill(status=204, headers={"HX-Redirect": "/login"}),
    )
    page.goto(f"{live_server}/code")
    expect(page).to_have_url(f"{live_server}/login", timeout=REFRESH_TIMEOUT_MS)


def test_ui_037_my_code_card_has_qr_timer_and_caption(page: Page, live_server):
    page.goto(f"{live_server}/code")
    card = page.locator(".qr-card")
    expect(card.locator(".qr-panel svg")).to_be_visible()
    expect(
        card.get_by_role("progressbar", name="Time until your code changes")
    ).to_be_visible()
    expect(card.get_by_text("Show a friend")).to_be_visible()
    expect(card.get_by_text("brightness")).to_be_visible()  # 07 section 3
    scan = page.get_by_role("link", name="Scan", exact=True).bounding_box()
    box = card.bounding_box()
    assert scan["y"] >= box["y"] + box["height"]  # Scan sits under the panel


def _timer_animation(page: Page):
    return page.locator(".qr-timer-fill").evaluate(
        "(el) => getComputedStyle(el).animationName"
    )


def test_ui_037_qr_timer_drains(page: Page, live_server):
    page.goto(f"{live_server}/code")
    assert _timer_animation(page) == "qr-drain"


def test_ui_055_qr_timer_stays_still_with_reduce_motion(page: Page, live_server):
    page.emulate_media(reduced_motion="reduce")
    page.goto(f"{live_server}/code")
    assert _timer_animation(page) == "none"
