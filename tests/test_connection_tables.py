import re
import sqlite3

import pytest

from app.db import connect, migrate

FAKE_PIN_HASH = "not-a-real-hash"  # fake data (ENG-047)


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def church_a(conn):
    return conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church A')"
    ).lastrowid


@pytest.fixture
def church_b(conn):
    return conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church B')"
    ).lastrowid


def _player(conn, church_id, n):
    return conn.execute(
        "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
        " VALUES (?, 'Test', ?, ?, 0, ?)",
        (f"pub-{n}", f"Player {n}", church_id, FAKE_PIN_HASH),
    ).lastrowid


def _connect(conn, low, high, scanner=None, same_church=0):
    return conn.execute(
        "INSERT INTO connection (player_low_id, player_high_id, scanner_id, is_same_church)"
        " VALUES (?, ?, ?, ?)",
        (low, high, low if scanner is None else scanner, same_church),
    ).lastrowid


@pytest.fixture
def pair(conn, church_a, church_b):
    return _player(conn, church_a, 1), _player(conn, church_b, 2)


def test_data_020_connection_saves_a_pair(conn, pair):
    low, high = pair
    row_id = _connect(conn, low, high, scanner=high)
    row = conn.execute("SELECT * FROM connection WHERE id = ?", (row_id,)).fetchone()
    assert (row["player_low_id"], row["player_high_id"]) == (low, high)
    assert row["scanner_id"] == high
    assert row["question_category"] is None


def test_data_020_same_pair_twice_is_refused(conn, pair):
    low, high = pair
    _connect(conn, low, high, scanner=low)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        _connect(conn, low, high, scanner=high)


def test_data_020_same_pair_in_opposite_order_is_refused(conn, pair):
    low, high = pair
    _connect(conn, low, high)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        _connect(conn, high, low, scanner=high)
    assert conn.execute("SELECT count(*) FROM connection").fetchone()[0] == 1


def test_game_014_player_cannot_connect_with_themselves(conn, pair):
    low, _ = pair
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        _connect(conn, low, low)


def test_data_001_scanner_must_be_one_of_the_pair(conn, pair, church_a):
    low, high = pair
    outsider = _player(conn, church_a, 3)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        _connect(conn, low, high, scanner=outsider)


def test_data_001_connection_needs_real_players(conn, pair):
    low, _ = pair
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        _connect(conn, low, 9999)


@pytest.mark.parametrize("category", ["Favorite verse", "", "verse; DROP"])
def test_data_001_question_category_is_a_short_key(conn, pair, category):
    low, high = pair
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO connection"
            " (player_low_id, player_high_id, scanner_id, question_category, is_same_church)"
            " VALUES (?, ?, ?, ?, 0)",
            (low, high, low, category),
        )


def test_data_021_church_bonus_saved_once_per_player(conn, pair, church_a, church_b):
    low, high = pair
    first = _connect(conn, low, high)
    other = _player(conn, church_b, 3)
    second = _connect(conn, low, other)
    conn.execute(
        "INSERT INTO church_met (player_id, church_id, connection_id) VALUES (?, ?, ?)",
        (low, church_b, first),
    )
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute(
            "INSERT INTO church_met (player_id, church_id, connection_id) VALUES (?, ?, ?)",
            (low, church_b, second),
        )
    # GAME-011: judged for each player on their own, so the other player still gets theirs.
    conn.execute(
        "INSERT INTO church_met (player_id, church_id, connection_id) VALUES (?, ?, ?)",
        (high, church_a, first),
    )
    assert conn.execute("SELECT count(*) FROM church_met").fetchone()[0] == 2


def test_data_001_church_met_needs_a_real_connection(conn, pair, church_b):
    low, _ = pair
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute(
            "INSERT INTO church_met (player_id, church_id, connection_id) VALUES (?, ?, 9999)",
            (low, church_b),
        )


def test_data_004_connection_created_at_is_utc(conn, pair):
    row_id = _connect(conn, *pair)
    created = conn.execute(
        "SELECT created_at FROM connection WHERE id = ?", (row_id,)
    ).fetchone()[0]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created)
