from playwright.sync_api import Page, expect

from app.auth import signup
from app.config import load_config
from app.db import connect
from tests.conftest import make_fake_pin

CHURCHES = ("Example Church A", "Example Church B")  # fake data (ENG-047)


def _seed_churches(db_path):
    conn = connect(db_path)
    conn.executemany(
        "INSERT OR IGNORE INTO church (name) VALUES (?)", [(n,) for n in CHURCHES]
    )
    conn.close()


def test_safe_002_join_flow_at_min_width(page: Page, live_server, test_db_path):
    _seed_churches(test_db_path)
    cfg = load_config()
    pin = make_fake_pin(cfg["auth"]["pin_digits"])
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(f"{live_server}/join")
    page.get_by_label("First name").fill("Test")
    page.get_by_label("Last name").fill("Browser Player 1")
    page.get_by_label("Church").select_option(label=CHURCHES[1])
    page.get_by_label("No").check()
    for field in (page.get_by_label("Church"), page.get_by_role("button", name="Next")):
        assert (
            field.bounding_box()["height"] >= cfg["ui"]["min_tap_target_px"]
        )  # UI-003
    page.get_by_role("button", name="Next").click()

    expect(
        page.get_by_label("PIN", exact=True)
    ).to_be_visible()  # HTMX swapped in PIN set
    page.get_by_label("PIN", exact=True).fill(pin)
    page.get_by_label("PIN again").fill(pin)
    page.get_by_role("button", name="Join the game").click()

    page.wait_for_url(f"{live_server}/")
    expect(page.get_by_role("link", name="Meet friends")).to_be_visible()
    assert (
        page.evaluate("document.documentElement.scrollWidth")
        <= cfg["ui"]["min_viewport_px"]
    )
    assert errors == []


def test_arch_032_login_flow_at_min_width(page: Page, live_server, test_db_path):
    _seed_churches(test_db_path)
    cfg = load_config()
    pin = make_fake_pin(cfg["auth"]["pin_digits"])
    conn = connect(test_db_path)
    church = conn.execute(
        "SELECT id FROM church WHERE name = ?", (CHURCHES[0],)
    ).fetchone()
    signup.create_player(
        conn, signup.Details("Test", "Browser Player 2", church["id"], False), pin
    )
    conn.close()
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(f"{live_server}/login")
    page.get_by_label("First name").fill("Test")
    page.get_by_label("Last name").fill("Browser Player 2")
    page.get_by_label("Church").select_option(label=CHURCHES[0])
    page.get_by_label("PIN").fill(pin)
    assert (
        page.get_by_role("button", name="Log in").bounding_box()["height"]
        >= cfg["ui"]["min_tap_target_px"]
    )
    page.get_by_role("button", name="Log in").click()

    page.wait_for_url(f"{live_server}/")
    expect(page.get_by_role("link", name="Meet friends")).to_be_visible()
    assert (
        page.evaluate("document.documentElement.scrollWidth")
        <= cfg["ui"]["min_viewport_px"]
    )
    assert errors == []
