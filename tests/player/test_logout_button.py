from playwright.sync_api import Page, expect

from app.auth import session, signup
from app.config import load_config
from app.db import connect
from tests.conftest import make_fake_pin

CHURCH = "Example Church A"  # fake data (ENG-047)


def test_arch_034_log_out_from_home_at_min_width(page: Page, live_server, test_db_path):
    cfg = load_config()
    pin = make_fake_pin(cfg["auth"]["pin_digits"])
    conn = connect(test_db_path)
    conn.execute("INSERT OR IGNORE INTO church (name) VALUES (?)", (CHURCH,))
    church = conn.execute("SELECT id FROM church WHERE name = ?", (CHURCH,)).fetchone()
    signup.create_player(
        conn, signup.Details("Test", "Browser Player 3", church["id"], False), pin
    )
    conn.close()
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(f"{live_server}/login")
    page.get_by_label("First name").fill("Test")
    page.get_by_label("Last name").fill("Browser Player 3")
    page.get_by_label("Church").select_option(label=CHURCH)
    page.get_by_label("PIN").fill(pin)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/")

    # UI-036: Log out sits in the settings menu, closed until the gear is tapped.
    settings = page.locator('summary[aria-label="Settings"]')
    log_out = page.get_by_role("button", name="Log out")
    expect(log_out).to_be_hidden()
    settings.click()
    expect(log_out).to_be_visible()
    tap_min = cfg["ui"]["min_tap_target_px"]
    assert settings.bounding_box()["height"] >= tap_min
    assert settings.bounding_box()["width"] >= tap_min
    assert log_out.bounding_box()["height"] >= tap_min
    assert (
        page.evaluate("document.documentElement.scrollWidth")
        <= cfg["ui"]["min_viewport_px"]
    )
    asked = []

    def answer(accept):
        def handle(dialog):
            asked.append(dialog.message)
            dialog.accept() if accept else dialog.dismiss()

        return handle

    # Cancel keeps the player on Home, still logged in.
    page.once("dialog", answer(accept=False))
    log_out.click()
    expect(log_out).to_be_visible()
    assert page.url == f"{live_server}/"
    assert session.COOKIE in {c["name"] for c in page.context.cookies()}

    # OK logs out.
    page.once("dialog", answer(accept=True))
    log_out.click()
    page.wait_for_url(f"{live_server}/login")
    expect(page.get_by_role("button", name="Log in")).to_be_visible()
    assert session.COOKIE not in {c["name"] for c in page.context.cookies()}
    assert asked == ["Log out on this phone?"] * 2
    assert errors == []
