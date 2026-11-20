import os
from pathlib import Path

from playwright.sync_api import Page, expect

from app.config import load_config
from app.db import connect
from tests.conftest import seed_fake_players
from tests.player.conftest import FAKE_PLAYER

# Test Player 5 is only used here, so saving an answer never changes another test's page.
# The helper names players by position, so the list keeps Players 1 to 4 as they are.
SEEDED = (
    FAKE_PLAYER.public_id,
    "testpid02",
    "testpid03",
    "testpid04",
    "testpid05",
    "testpid06",
)
FRIEND, VERSE_FRIEND = SEEDED[-2:]  # fake data (ENG-047)


def _fresh_connection(friend=FRIEND, category="food") -> int:
    """A pair with no answer yet. Chromium and WebKit share one test database."""
    db_path = Path(os.environ["SQ_DB_PATH"])
    ids = seed_fake_players(db_path, *SEEDED)
    conn = connect(db_path)
    try:
        low, high = sorted((ids[FAKE_PLAYER.public_id], ids[friend]))
        conn.execute(
            "INSERT OR IGNORE INTO connection (player_low_id, player_high_id,"
            " scanner_id, question_category, is_same_church) VALUES (?, ?, ?, ?, 1)",
            (low, high, ids[FAKE_PLAYER.public_id], category),
        )
        connection_id = conn.execute(
            "SELECT id FROM connection WHERE player_low_id = ? AND player_high_id = ?",
            (low, high),
        ).fetchone()[0]
        # The points go too, as in the retention cleanup, or a reused answer id would
        # look already paid (DATA-027).
        conn.execute(
            "DELETE FROM point_ledger WHERE source_type = 'icebreaker_answer'"
            " AND source_id IN (SELECT id FROM icebreaker_answer WHERE connection_id = ?)",
            (connection_id,),
        )
        conn.execute(
            "DELETE FROM icebreaker_answer WHERE connection_id = ?", (connection_id,)
        )
        return connection_id
    finally:
        conn.close()


def test_game_016_save_answer_on_the_icebreaker(page: Page, live_server):
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(f"{live_server}/connections/{_fresh_connection()}")
    page.get_by_label("Their answer").fill("Example answer")
    page.get_by_role("button", name="Save").click()
    points = load_config()["points"]["connect_same_church"]  # AI-013
    expect(page.get_by_role("status")).to_have_text(
        f"Saved! You earned {points} points."
    )
    expect(page.get_by_text("Example answer")).to_be_visible()
    expect(page.get_by_label("Their answer")).to_have_count(0)
    assert not errors, errors


def test_ui_002_long_answer_wraps_without_sideways_scroll(page: Page, live_server):
    page.goto(f"{live_server}/connections/{_fresh_connection()}")
    max_chars = int(page.get_by_label("Their answer").get_attribute("maxlength"))
    page.get_by_label("Their answer").fill("x" * max_chars)  # one long word
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_role("status")).to_be_visible()
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]


def test_wrap_012_verse_lists_fit_the_chosen_book(page: Page, live_server):
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(f"{live_server}/connections/{_fresh_connection(VERSE_FRIEND, 'verse')}")
    book = page.get_by_label("Book", exact=True)
    chapter = page.get_by_label("Chapter", exact=True)
    verse = page.get_by_label("Verse", exact=True)
    book.select_option("3 John")
    expect(chapter.locator("option")).to_have_count(1)
    expect(verse.locator("option")).to_have_count(15)
    book.select_option("John")
    expect(chapter.locator("option")).to_have_count(21)
    chapter.select_option("3")
    expect(verse.locator("option")).to_have_count(36)
    verse.select_option("16")
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_role("status")).to_be_visible()
    expect(page.get_by_text("John 3:16")).to_be_visible()
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= load_config()["ui"]["min_viewport_px"]
    assert not errors, errors
