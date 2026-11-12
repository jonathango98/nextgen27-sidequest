"""Blind box math (GAME-070, GAME-071, GAME-074, DATA-031).

Every number is built from game-config.yaml, never hardcoded (AI-013).
"""

import pytest

from app.config import load_config
from app.db import connect, migrate
from app.services import blind_boxes, churches
from app.services.blind_boxes import claimable, claimed_count, earned, progress
from app.services.game_state import set_state

CFG = load_config()
BOX = CFG["blind_box"]
STEP = BOX["milestone_points"]
MAX = BOX["max_per_player"]
JOIN = CFG["points"]["join"]


def test_game_070_one_box_per_milestone():
    assert earned(0, BOX) == 0
    assert earned(STEP - 1, BOX) == 0
    assert earned(STEP, BOX) == 1
    assert earned(2 * STEP - 1, BOX) == 1


def test_game_070_progress_counts_points_since_last_milestone():
    # Rule text: "for example 120 of 300", here built from config.
    since = STEP // 3
    bar = progress(STEP + since, BOX)
    assert (bar.points, bar.milestone, bar.all_earned) == (since, STEP, False)
    assert bar.percent == since * 100 // STEP


def test_game_070_new_player_bar_starts_at_join_points():
    bar = progress(JOIN, BOX)
    assert bar.points == JOIN % STEP
    assert not bar.all_earned


def test_game_070_negative_score_earns_nothing_and_bar_is_empty():
    # GAME-004: only an admin revocation lowers a score, and it can dip below 0.
    assert earned(-STEP, BOX) == 0
    bar = progress(-1, BOX)
    assert (bar.points, bar.percent, bar.all_earned) == (0, 0, False)


def test_game_071_capped_at_max():
    assert earned(MAX * STEP, BOX) == MAX
    assert earned((MAX + 2) * STEP, BOX) == MAX


def test_game_071_bar_full_once_every_box_is_earned():
    bar = progress(MAX * STEP, BOX)
    assert bar.all_earned
    assert bar.percent == 100
    assert progress(MAX * STEP - 1, BOX).all_earned is False


def test_game_074_claimable_is_earned_minus_claimed():
    assert claimable(MAX, 1) == MAX - 1
    assert claimable(1, 1) == 0


def test_game_074_never_below_zero():
    assert claimable(0, 1) == 0


def test_game_074_nothing_claimed_before_handout(tmp_path):
    # The BoxClaim table comes with blind-box.handout (DATA-026). Until then, nobody has claimed.
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    assert claimed_count(conn, "testpid01") == 0
    conn.close()


def test_game_070_071_074_worked_example_e10():
    # E10: Player J has 905 points (the max boxes and a bit), has claimed 1, can claim the rest.
    score = MAX * STEP + 5
    assert earned(score, BOX) == MAX
    assert claimable(earned(score, BOX), 1) == MAX - 1
    # At 1,500 points, boxes earned is still the max.
    assert earned((MAX + 2) * STEP, BOX) == MAX


def test_game_074_worked_example_e11_revocation_after_claim():
    # E11: Player K has 610 points, earned 2 and claimed 2. A 20 point revocation leaves 590.
    before = 2 * STEP + 10
    after = before - 20
    assert earned(before, BOX) == 2
    assert earned(after, BOX) == 1
    # Claimed stays 2, so claimable is 0, never below 0. Player K keeps both boxes.
    assert claimable(earned(after, BOX), 2) == 0


FAKE_PIN_ENV = "SQ_PREVIEW_PLAYER_PIN"


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    churches.seed_examples(conn)
    yield conn
    conn.close()


def _preview_score(conn):
    first, last = blind_boxes.PREVIEW_PLAYER
    return conn.execute(
        "SELECT coalesce(sum(l.amount), 0) FROM point_ledger l"
        " JOIN player p ON p.id = l.player_id WHERE p.first_name = ? AND p.last_name = ?",
        (first, last),
    ).fetchone()[0]


def test_eng_113_preview_player_has_a_ready_box_once(conn, monkeypatch, fake_pin):
    monkeypatch.setenv(FAKE_PIN_ENV, fake_pin)
    added = blind_boxes.seed_preview(conn, CFG)
    assert added == [" ".join(blind_boxes.PREVIEW_PLAYER)]
    score = _preview_score(conn)
    # Past the first milestone but short of the next, so Home shows a part-full bar.
    assert earned(score, BOX) == 1
    assert 0 < progress(score, BOX).points < STEP
    # A restart adds no one and gives nothing twice (AI-047).
    assert blind_boxes.seed_preview(conn, CFG) == []
    assert _preview_score(conn) == score


def test_eng_113_preview_box_seed_needs_the_preview_pin(conn, monkeypatch):
    monkeypatch.delenv(FAKE_PIN_ENV, raising=False)
    assert blind_boxes.seed_preview(conn, CFG) == []
    assert _preview_score(conn) == 0


def test_eng_113_preview_box_seed_gives_no_points_while_paused(
    conn, monkeypatch, fake_pin
):
    monkeypatch.setenv(FAKE_PIN_ENV, fake_pin)
    set_state(conn, "paused")
    blind_boxes.seed_preview(conn, CFG)
    assert earned(_preview_score(conn), BOX) == 0
