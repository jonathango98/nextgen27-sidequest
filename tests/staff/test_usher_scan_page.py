import time

import pytest
from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services import qr
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_PASSWORD = "test password only 1"
FAKE_PIN_HASH = "not-a-real-hash"
CHURCH = "Example Church A"
QR = load_config()["qr"]
# Chromium's test camera: a moving test picture instead of a real one, allowed without a prompt.
FAKE_CAMERA = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"]


@pytest.fixture
def scan_page(playwright, live_server, browser_context_args):
    browser = playwright.chromium.launch(args=FAKE_CAMERA)
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append(str(e)))
    yield page
    context.close()
    browser.close()


def _seed(test_db_path, suffix):
    conn = connect(test_db_path)
    username = f"test-usher-scan-{suffix}"
    create_account(conn, username, FAKE_PASSWORD, "usher")
    conn.execute("INSERT OR IGNORE INTO church (name) VALUES (?)", (CHURCH,))
    public_id = f"testscan{suffix}"
    conn.execute(
        "INSERT INTO player"
        " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
        " VALUES (?, 'Scannable', ?, (SELECT id FROM church WHERE name = ?), 0, ?)",
        (public_id, f"Zimmerman {suffix}", CHURCH, FAKE_PIN_HASH),
    )
    conn.close()
    return username, public_id


def _open_console(page: Page, live_server, username):
    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/usher")


def _start_camera(page: Page):
    page.get_by_role("button", name="Scan", exact=True).click()
    page.wait_for_function(
        "document.querySelector('video').readyState >= 2", timeout=5000
    )


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def _handle(page: Page, code: str):
    page.evaluate("code => window.sqScanner.handle(code)", code)


def test_game_112_scan_a_player_at_min_width(scan_page, live_server, test_db_path):
    username, public_id = _seed(test_db_path, "a")
    _open_console(scan_page, live_server, username)
    _fits(scan_page)
    _start_camera(scan_page)

    _handle(scan_page, qr.payload(qr.PLAYER_KIND, public_id, time.time(), QR))
    card = scan_page.locator("[data-player-card]")
    expect(card).to_contain_text("Scannable Z.")
    expect(card).to_contain_text(CHURCH)
    expect(card).not_to_contain_text("Zimmerman")
    # The server's answer replaces "Got it!", and the camera stops until Scan again.
    expect(scan_page.locator(".scan-result")).to_be_hidden()
    again = scan_page.get_by_role("button", name="Scan again")
    expect(again).to_be_visible()
    _fits(scan_page)

    again.click()
    expect(card).to_have_count(0)
    expect(again).to_be_hidden()
    assert scan_page.problems == []


def test_arch_022_expired_code_shows_the_message(scan_page, live_server, test_db_path):
    username, public_id = _seed(test_db_path, "b")
    _open_console(scan_page, live_server, username)
    _start_camera(scan_page)
    steps = QR["accepted_previous_steps"] + 2
    old = time.time() - QR["rotation_seconds"] * steps
    _handle(scan_page, qr.payload(qr.PLAYER_KIND, public_id, old, QR))
    expect(scan_page.locator('[data-error-code="CODE_EXPIRED"]')).to_be_visible()
    expect(scan_page.locator("[data-player-card]")).to_have_count(0)
    expect(scan_page.get_by_role("button", name="Scan again")).to_be_visible()


def test_arch_025_other_code_keeps_scanning(scan_page, live_server, test_db_path):
    username, _ = _seed(test_db_path, "c")
    _open_console(scan_page, live_server, username)
    _start_camera(scan_page)
    _handle(scan_page, "https://example.com/menu")
    expect(scan_page.get_by_text("This isn't a Side Quest code.")).to_be_visible()
    expect(scan_page.get_by_role("button", name="Scan again")).to_be_hidden()


def test_ui_035_usher_console_has_one_main_button(scan_page, live_server, test_db_path):
    username, public_id = _seed(test_db_path, "d")
    _open_console(scan_page, live_server, username)
    main_buttons = scan_page.locator(".button:not(.button-secondary):visible")
    expect(main_buttons).to_have_count(1)
    _start_camera(scan_page)
    _handle(scan_page, qr.payload(qr.PLAYER_KIND, public_id, time.time(), QR))
    expect(scan_page.get_by_role("button", name="Scan again")).to_be_visible()
    expect(main_buttons).to_have_count(1)


def test_game_112_camera_stays_off_until_scan_is_tapped(
    scan_page, live_server, test_db_path
):
    username, _ = _seed(test_db_path, "e")
    _open_console(scan_page, live_server, username)
    assert scan_page.evaluate("document.querySelector('video').srcObject") is None
    _start_camera(scan_page)
    assert scan_page.evaluate(
        "document.querySelector('video').srcObject.getTracks()"
        ".some(t => t.readyState === 'live')"
    )
    expect(scan_page.get_by_role("button", name="Scan", exact=True)).to_be_hidden()
