from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030). A long church name, to check the buttons wrap.
FAKE_PASSWORD = "test password only 1"
FAKE_PIN_HASH = "not-a-real-hash"
CHURCH = "Example Church With A Very Long Name In Downtown A"


def _fits(page: Page):
    width = load_config()["ui"]["min_viewport_px"]  # UI-002
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def _seed(test_db_path, browser_name):
    conn = connect(test_db_path)
    username = f"test-usher-find-{browser_name}"
    create_account(conn, username, FAKE_PASSWORD, "usher")
    conn.execute("INSERT OR IGNORE INTO church (name) VALUES (?)", (CHURCH,))
    conn.execute(
        "INSERT INTO player"
        " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
        " VALUES (?, ?, ?, (SELECT id FROM church WHERE name = ?), 0, ?)",
        (
            f"testfind{browser_name}",
            "Findable",
            f"Zimmerman {browser_name}",
            CHURCH,
            FAKE_PIN_HASH,
        ),
    )
    conn.close()
    return username


def test_game_113_find_a_player_at_min_width(
    page: Page, live_server, test_db_path, browser_name
):
    username = _seed(test_db_path, browser_name)
    tap_min = load_config()["ui"]["min_tap_target_px"]  # UI-003
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(f"{live_server}/staff/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(FAKE_PASSWORD)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(f"{live_server}/usher")
    page.get_by_role("link", name="Find player").click()
    expect(page.get_by_role("heading", name="Find player")).to_be_visible()
    _fits(page)

    # Search by last name. Only the initial comes back (SAFE-004).
    page.get_by_label("Name").fill("zimmerman")
    page.get_by_role("button", name="Search").click()
    found = page.get_by_role("navigation", name="Players found").get_by_role("link")
    expect(found.first).to_contain_text(f"Findable Z. · {CHURCH}")
    assert found.first.bounding_box()["height"] >= tap_min
    _fits(page)

    # Pick them. The card shows who it is, with nothing extra.
    found.first.click()
    card = page.locator("[data-player-card]")
    expect(card).to_contain_text("Findable Z.")
    expect(card).to_contain_text(CHURCH)
    expect(card).not_to_contain_text("Zimmerman")
    _fits(page)

    # And back again.
    page.get_by_role("link", name="Find another").click()
    expect(page.get_by_label("Name")).to_be_visible()
    assert errors == []
