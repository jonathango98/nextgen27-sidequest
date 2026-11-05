import math
from dataclasses import fields
from fractions import Fraction

import pytest

from app.config import load_config
from app.db import connect, migrate
from app.services import churches, leaderboards, points
from app.services.game_state import set_state

CONFIG = load_config()
CFG = CONFIG["leaderboard"]
K = CFG["church_score_prior_players"]
JOIN = CONFIG["points"]["join"]
BOOTH = CONFIG["points"]["booth_visit"]
FAKE_ADMIN_ID = 7  # fake staff id (ENG-047)
FAKE_PIN_ENV = "SQ_PREVIEW_PLAYER_PIN"


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


def _church(conn, name):
    conn.execute("INSERT OR IGNORE INTO church (name) VALUES (?)", (name,))
    return conn.execute("SELECT id FROM church WHERE name = ?", (name,)).fetchone()[0]


def _player(conn, n, church="Example Church A", earned=0, under_18=False):
    """Fake Test Player n (ENG-047) with join points, plus `earned` points from a booth."""
    player_id = conn.execute(
        "INSERT INTO player"
        " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
        " VALUES (?, 'Test', ?, ?, ?, 'not-a-real-hash')",
        (f"fake-{n}", f"Player {n}", _church(conn, church), int(under_18)),
    ).lastrowid
    points.award_join(conn, player_id=player_id, amount=JOIN, while_paused=True)
    if earned:
        _earn(conn, player_id, earned)
    return player_id


def _earn(conn, player_id, amount, source_id=1):
    return points.award(
        conn,
        player_id=player_id,
        reason_code="booth_visit",
        amount=amount,
        source_type="booth",
        source_id=source_id,
    )


def _at(conn, ledger_id, when):
    conn.execute(
        "UPDATE point_ledger SET created_at = ? WHERE id = ?", (when, ledger_id)
    )


def _last_award(conn, player_id):
    return conn.execute(
        "SELECT max(id) FROM point_ledger WHERE player_id = ?", (player_id,)
    ).fetchone()[0]


def _expected(total, counted, average):
    # GAME-089 as written in 02: (their points added up + k x overall average) / (their number + k).
    return math.floor(Fraction(total + K * average, counted + K) + Fraction(1, 2))


def test_game_089_worked_example():
    # 02 section 7: the overall average is 90. Church A counts 100, 80, 60 (two only joined).
    church_a = leaderboards.church_score(100 + 80 + 60, 3, K, Fraction(90))
    church_b = leaderboards.church_score(300, 1, K, Fraction(90))
    assert leaderboards.shown(church_a) == _expected(240, 3, 90)
    assert leaderboards.shown(church_b) == _expected(300, 1, 90)
    # One player with 300 points does not give Church B a score of 300.
    assert leaderboards.shown(church_b) < 300


def test_game_089_score_is_shown_rounded_half_up():
    assert leaderboards.shown(Fraction(173, 2)) == 87
    assert leaderboards.shown(Fraction(171, 2)) == 86
    assert leaderboards.shown(Fraction(86)) == 86


def test_game_089_join_only_players_do_not_count(conn):
    _player(conn, 1, "Example Church A", earned=4 * BOOTH)
    _player(conn, 2, "Example Church A")  # only joined
    _player(conn, 3, "Example Church B", earned=2 * BOOTH)
    a, b = JOIN + 4 * BOOTH, JOIN + 2 * BOOTH
    average = Fraction(a + b, 2)
    board = leaderboards.top_churches(conn, CFG)
    assert [(r.church, r.score) for r in board] == [
        ("Example Church A", _expected(a, 1, average)),
        ("Example Church B", _expected(b, 1, average)),
    ]


def test_game_089_fully_revoked_award_is_not_active(conn):
    player_id = _player(conn, 1, earned=BOOTH)
    conn.execute(
        "INSERT INTO point_ledger (player_id, amount, reason_code, note, created_by)"
        " VALUES (?, ?, 'manual_revoke', 'Test revoke only', ?)",
        (player_id, -BOOTH, FAKE_ADMIN_ID),
    )
    assert leaderboards.top_churches(conn, CFG) == []


def test_game_081_one_big_player_cannot_carry_a_church(conn):
    _player(conn, 1, "Example Church A", earned=2 * BOOTH)
    _player(conn, 2, "Example Church A", earned=2 * BOOTH)
    big = _player(conn, 3, "Example Church B", earned=30 * BOOTH)
    [top_player] = leaderboards.top_players(conn, {**CFG, "main_screen_top_n": 1})
    assert top_player.score == points.score(conn, big)
    church_b = next(
        r
        for r in leaderboards.top_churches(conn, CFG)
        if r.church == "Example Church B"
    )
    assert church_b.score < top_player.score


def test_game_082_church_needs_min_active_players(conn):
    needed = CFG["church_min_players"]
    for n in range(needed):
        _player(conn, n + 1, "Example Church A", earned=BOOTH)
    for n in range(needed - 1):
        _player(conn, needed + n + 1, "Example Church B", earned=BOOTH)
    _player(conn, 2 * needed + 1, "Example Church B")  # only joined, never counts
    assert [r.church for r in leaderboards.top_churches(conn, CFG)] == [
        "Example Church A"
    ]


def test_game_083_boards_show_top_n_rows(conn):
    top_n = CFG["main_screen_top_n"]
    for n in range(top_n + 1):
        _player(conn, n + 1, f"Example Church {n}", earned=(n + 1) * BOOTH)
    players = leaderboards.top_players(conn, CFG)
    church_board = leaderboards.top_churches(conn, CFG)
    assert len(players) == top_n
    assert len(church_board) == top_n
    # Highest first, so the lowest scorer is the one left off.
    assert [p.score for p in players] == sorted(
        (p.score for p in players), reverse=True
    )
    assert "Example Church 0" not in {p.church for p in players}
    assert "Example Church 0" not in {r.church for r in church_board}


def test_game_084_player_tie_goes_to_first_to_reach(conn):
    later = _player(conn, 1, "Example Church A", earned=BOOTH)
    earlier = _player(conn, 2, "Example Church B", earned=BOOTH)
    # The Church B player reached the score first, though their rows were saved later.
    _at(conn, _last_award(conn, later), "2027-01-10T12:00:05Z")
    _at(conn, _last_award(conn, earlier), "2027-01-10T12:00:01Z")
    board = leaderboards.top_players(conn, CFG)
    assert [p.church for p in board] == ["Example Church B", "Example Church A"]
    assert board[0].score == board[1].score


def test_game_084_same_second_goes_to_the_earlier_row(conn):
    _player(conn, 1, "Example Church A", earned=BOOTH)
    _player(conn, 2, "Example Church B", earned=BOOTH)
    conn.execute("UPDATE point_ledger SET created_at = '2027-01-10T12:00:00Z'")
    churches_in_order = [p.church for p in leaderboards.top_players(conn, CFG)]
    assert churches_in_order == ["Example Church A", "Example Church B"]


def test_game_084_church_tie_goes_to_first_to_reach(conn):
    a = _player(conn, 1, "Example Church A", earned=BOOTH)
    b = _player(conn, 2, "Example Church B", earned=BOOTH)
    _at(conn, _last_award(conn, a), "2027-01-10T12:00:05Z")
    _at(conn, _last_award(conn, b), "2027-01-10T12:00:01Z")
    board = leaderboards.top_churches(conn, CFG)
    assert [r.church for r in board] == ["Example Church B", "Example Church A"]
    assert board[0].score == board[1].score


def test_game_084_church_ranked_by_exact_score_before_the_tie_break(conn):
    # Church B is a point ahead but reached it later. Its exact score is higher, so it still
    # ranks first, whether or not the two round to the same shown number.
    a = _player(conn, 1, "Example Church A", earned=BOOTH)
    b = _player(conn, 2, "Example Church B", earned=BOOTH)
    _earn(conn, b, 1, source_id=2)
    _at(conn, _last_award(conn, a), "2027-01-10T12:00:01Z")
    _at(conn, _last_award(conn, b), "2027-01-10T12:00:05Z")
    board = leaderboards.top_churches(conn, CFG)
    assert [r.church for r in board] == ["Example Church B", "Example Church A"]


def test_game_086_safe_004_rows_never_hold_a_last_name(conn):
    _player(conn, 1, earned=BOOTH)
    assert {f.name for f in fields(leaderboards.PlayerRow)} == {
        "first_name",
        "last_initial",
        "church",
        "dot",
        "score",
    }
    [row] = leaderboards.top_players(conn, CFG)
    assert (row.first_name, row.last_initial, row.church) == (
        "Test",
        "P",
        "Example Church A",
    )


def test_safe_019_under_18_players_are_listed_like_everyone(conn):
    _player(conn, 1, earned=BOOTH, under_18=True)
    _player(conn, 2, "Example Church B", earned=BOOTH, under_18=True)
    assert len(leaderboards.top_players(conn, CFG)) == 2
    assert len(leaderboards.top_churches(conn, CFG)) == 2


def test_game_087_empty_boards(conn):
    _player(conn, 1)  # only joined: on the player board, but no church counts yet
    assert len(leaderboards.top_players(conn, CFG)) == 1
    assert leaderboards.top_churches(conn, CFG) == []


def test_game_089_shipped_config_is_understood():
    leaderboards.check_config(CFG)


@pytest.mark.parametrize(
    "key,value",
    [("church_score_denominator", "all_players"), ("tie_break", "random")],
)
def test_game_089_unknown_rule_in_config_is_refused(key, value):
    with pytest.raises(leaderboards.LeaderboardConfigError):
        leaderboards.check_config({**CFG, key: value})


def _preview_points(conn):
    return conn.execute(
        "SELECT count(*), coalesce(sum(amount), 0) FROM point_ledger WHERE reason_code = ?",
        (leaderboards.PREVIEW_REASON,),
    ).fetchone()


def test_eng_113_preview_seeds_ranked_example_players_once(conn, monkeypatch, fake_pin):
    monkeypatch.setenv(FAKE_PIN_ENV, fake_pin)
    churches.seed_examples(conn)
    added = leaderboards.seed_preview(conn, CONFIG)
    assert added == [f"{f} {last}" for (f, last), _, _ in leaderboards.PREVIEW_PLAYERS]
    expected = sum(v for _, _, v in leaderboards.PREVIEW_PLAYERS) * BOOTH
    assert tuple(_preview_points(conn)) == (len(leaderboards.PREVIEW_PLAYERS), expected)
    # Every award went through the points service, so each has its audit row (AI-041).
    audited = conn.execute(
        "SELECT count(*) FROM audit_log WHERE action = 'points_award'"
    ).fetchone()[0]
    assert audited == 2 * len(leaderboards.PREVIEW_PLAYERS)  # join and example points
    assert len(leaderboards.top_churches(conn, CFG)) == 2
    # A restart adds nothing twice.
    assert leaderboards.seed_preview(conn, CONFIG) == []
    assert tuple(_preview_points(conn)) == (len(leaderboards.PREVIEW_PLAYERS), expected)


def test_eng_113_preview_seed_needs_the_preview_pin(conn, monkeypatch):
    monkeypatch.delenv(FAKE_PIN_ENV, raising=False)
    churches.seed_examples(conn)
    assert leaderboards.seed_preview(conn, CONFIG) == []
    assert tuple(_preview_points(conn)) == (0, 0)


def test_eng_113_preview_seed_gives_no_points_while_paused(conn, monkeypatch, fake_pin):
    monkeypatch.setenv(FAKE_PIN_ENV, fake_pin)
    churches.seed_examples(conn)
    set_state(conn, "paused")
    leaderboards.seed_preview(conn, CONFIG)
    assert tuple(_preview_points(conn)) == (0, 0)


def test_ui_008_a_church_keeps_one_dot_color_on_both_boards(conn):
    for n in range(leaderboards.DOT_COLORS + 1):
        _player(conn, n + 1, f"Example Church {n}", earned=BOOTH)
    players = {p.church: p.dot for p in leaderboards.top_players(conn, CFG)}
    church_board = {r.church: r.dot for r in leaderboards.top_churches(conn, CFG)}
    assert players == church_board
    assert set(players.values()) <= set(range(leaderboards.DOT_COLORS))
