import sqlite3
import threading

import pytest

from app.config import load_config
from app.db import connect, migrate
from app.services.game_state import GameNotOn, set_state
from app.services.points import AlreadyAwarded, award, award_join, score

FAKE_PIN_HASH = "not-a-real-hash"  # fake data (ENG-047)
# Real amounts from config, never a hardcoded game number (AI-013).
AMOUNT = load_config()["points"]["connect_other_church"]
JOIN_AMOUNT = load_config()["points"]["join"]
SOURCE = {"source_type": "connection", "source_id": 1}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "side-quest.db"


@pytest.fixture
def conn(db_path):
    conn = connect(db_path)
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def player(conn):
    church = conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church A')"
    ).lastrowid
    return conn.execute(
        "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
        " VALUES ('pub-1', 'Test', 'Player 1', ?, 0, ?)",
        (church, FAKE_PIN_HASH),
    ).lastrowid


def _give(conn, player, **overrides):
    args = {
        "player_id": player,
        "reason_code": "connect_other_church",
        "amount": AMOUNT,
        **SOURCE,
    }
    return award(conn, **{**args, **overrides})


def _count(conn, table):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_arch_040_award_saved_once_with_audit_row(conn, player):
    ledger_id = _give(conn, player)
    row = conn.execute(
        "SELECT * FROM point_ledger WHERE id = ?", (ledger_id,)
    ).fetchone()
    assert (row["player_id"], row["amount"], row["reason_code"]) == (
        player,
        AMOUNT,
        "connect_other_church",
    )
    assert row["created_by"] is None
    audit = conn.execute("SELECT * FROM audit_log").fetchall()
    assert [
        (a["actor_type"], a["action"], a["target_type"], a["target_id"]) for a in audit
    ] == [("system", "points_award", "point_ledger", ledger_id)]
    assert not conn.in_transaction  # its own transaction was committed


@pytest.mark.parametrize(("state", "code"), [("paused", "PAUSED"), ("off", "GAME_OFF")])
def test_arch_041_award_refused_while_paused_or_off(conn, player, state, code):
    set_state(conn, state)
    with pytest.raises(GameNotOn) as refused:
        _give(conn, player)
    assert refused.value.error_code == code


def test_arch_040_refused_award_writes_nothing(conn, player):
    set_state(conn, "paused")
    with pytest.raises(GameNotOn):
        _give(conn, player)
    assert _count(conn, "point_ledger") == 0
    assert _count(conn, "audit_log") == 0
    assert not conn.in_transaction


def test_data_027_same_award_twice_given_once(conn, player):
    _give(conn, player)
    with pytest.raises(AlreadyAwarded):
        _give(conn, player)
    assert score(conn, player) == AMOUNT
    assert _count(conn, "audit_log") == 1


def test_data_027_other_records_still_pay(conn, player):
    _give(conn, player)
    _give(conn, player, source_id=2)
    _give(conn, player, reason_code="connect_new_church_bonus")
    assert _count(conn, "point_ledger") == 3


def test_data_027_database_refuses_double_pay(conn, player):
    # The unique index stops it even if code skips the check (DATA-027).
    _give(conn, player)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute(
            "INSERT INTO point_ledger (player_id, amount, reason_code, source_type, source_id)"
            " VALUES (?, ?, 'connect_other_church', 'connection', 1)",
            (player, AMOUNT),
        )


def test_data_027_two_awards_at_once_given_once(db_path, conn, player):
    # Two phones tap at the same moment: two connections, released together.
    start = threading.Barrier(2)
    results = []

    def tap():
        own = connect(db_path)
        try:
            start.wait()
            results.append(_give(own, player))
        except AlreadyAwarded:
            results.append("already")
        finally:
            own.close()

    threads = [threading.Thread(target=tap) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results, key=str).count("already") == 1
    assert score(conn, player) == AMOUNT
    assert _count(conn, "audit_log") == 1


def test_data_030_score_is_sum_of_ledger(conn, player):
    assert score(conn, player) == 0
    _give(conn, player)
    _give(conn, player, source_id=2)
    assert score(conn, player) == 2 * AMOUNT


@pytest.mark.parametrize("amount", [0, -AMOUNT])
def test_game_004_system_award_must_be_positive(conn, player, amount):
    with pytest.raises(ValueError):
        _give(conn, player, amount=amount)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO point_ledger (player_id, amount, reason_code, source_type, source_id)"
            " VALUES (?, ?, 'connect_other_church', 'connection', 1)",
            (player, amount),
        )
    assert score(conn, player) == 0


def test_data_027_system_award_must_name_its_record(conn, player):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO point_ledger (player_id, amount, reason_code) VALUES (?, ?, 'join')",
            (player, AMOUNT),
        )


def _join(conn, player, while_paused=True):
    return award_join(
        conn, player_id=player, amount=JOIN_AMOUNT, while_paused=while_paused
    )


def test_game_040_join_points_saved_with_audit_row(conn, player):
    ledger_id = _join(conn, player)
    row = conn.execute(
        "SELECT * FROM point_ledger WHERE id = ?", (ledger_id,)
    ).fetchone()
    assert (row["reason_code"], row["source_type"]) == ("join", "player")
    assert score(conn, player) == JOIN_AMOUNT
    assert _count(conn, "audit_log") == 1


def test_game_040_join_points_paid_once(conn, player):
    _join(conn, player)
    with pytest.raises(AlreadyAwarded):
        _join(conn, player)
    assert score(conn, player) == JOIN_AMOUNT


def test_game_044_join_points_paid_while_paused(conn, player):
    set_state(conn, "paused")
    _join(conn, player)
    assert score(conn, player) == JOIN_AMOUNT


def test_game_044_only_join_points_pay_while_paused(conn, player):
    set_state(conn, "paused")
    _join(conn, player)
    with pytest.raises(GameNotOn):
        _give(conn, player)
    assert score(conn, player) == JOIN_AMOUNT


def test_game_044_no_join_points_while_paused_when_config_says_no(conn, player):
    set_state(conn, "paused")
    assert _join(conn, player, while_paused=False) is None
    assert _count(conn, "point_ledger") == 0
    assert _count(conn, "audit_log") == 0


@pytest.mark.parametrize("while_paused", [True, False])
def test_game_108_join_points_refused_while_off(conn, player, while_paused):
    set_state(conn, "off")
    with pytest.raises(GameNotOn) as refused:
        _join(conn, player, while_paused=while_paused)
    assert refused.value.error_code == "GAME_OFF"
    assert _count(conn, "point_ledger") == 0


@pytest.mark.parametrize("amount", [0, -JOIN_AMOUNT])
def test_game_004_join_points_must_be_positive(conn, player, amount):
    with pytest.raises(ValueError):
        award_join(conn, player_id=player, amount=amount, while_paused=True)


def test_arch_040_award_joins_callers_transaction(conn, player):
    # A quest saves its record and its points together, or neither.
    conn.execute("BEGIN IMMEDIATE")
    _give(conn, player)
    assert conn.in_transaction  # award() left the caller's transaction open
    conn.execute("ROLLBACK")
    assert _count(conn, "point_ledger") == 0
    assert _count(conn, "audit_log") == 0
