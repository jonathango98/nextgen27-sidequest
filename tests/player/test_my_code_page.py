import os
from pathlib import Path

from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect

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


def test_api_032_scanned_player_sees_note_without_tapping(page: Page, live_server):
    db_path = Path(os.environ["SQ_DB_PATH"])
    conn = connect(db_path)
    ids = dict(conn.execute("SELECT public_id, id FROM player").fetchall())
    me, them = ids["testpid01"], ids["testpid04"]
    # Each browser run starts with the pair not yet saved.
    conn.execute(
        "DELETE FROM connection WHERE player_low_id = ? AND player_high_id = ?",
        (me, them),
    )
    page.goto(f"{live_server}/code")
    expect(page.locator(".qr-panel svg")).to_be_visible()
    # Test Player 4 scans this player's code on another phone.
    conn.execute(
        "INSERT INTO connection (player_low_id, player_high_id, scanner_id,"
        " question_category, is_same_church) VALUES (?, ?, ?, 'hobby', 1)",
        (me, them, them),
    )
    conn.close()
    poll_ms = load_config()["qr"]["incoming_poll_seconds"] * 1000
    note = page.get_by_role("link", name="Test just scanned you!")
    expect(note).to_be_visible(timeout=poll_ms + REFRESH_TIMEOUT_MS)
    expect(note).to_contain_text("What do you do for fun?")
