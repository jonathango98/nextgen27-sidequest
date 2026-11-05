import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.db import MIGRATIONS_DIR, DatabaseError, connect, db_path_from_env, migrate
from app.main import create_app

FAKE_PIN_HASH = "not-a-real-hash"  # fake data (ENG-047)


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


def _add_church(conn, name="Example Church A"):
    return conn.execute("INSERT INTO church (name) VALUES (?)", (name,)).lastrowid


def _add_player(conn, church_id, first="Test", last="Player 1", public_id="pub-1"):
    return conn.execute(
        "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
        " VALUES (?, ?, ?, ?, 0, ?)",
        (public_id, first, last, church_id, FAKE_PIN_HASH),
    ).lastrowid


def test_data_040_migrations_apply_in_order_and_once(tmp_path):
    (tmp_path / "0002_second.sql").write_text(
        "CREATE TABLE second (id INTEGER PRIMARY KEY);"
    )
    (tmp_path / "0001_first.sql").write_text(
        "CREATE TABLE first (id INTEGER PRIMARY KEY);"
    )
    conn = connect(tmp_path / "t.db")
    assert migrate(conn, tmp_path) == ["0001_first.sql", "0002_second.sql"]
    assert migrate(conn, tmp_path) == []
    versions = [
        r["version"] for r in conn.execute("SELECT version FROM schema_migration")
    ]
    assert versions == [1, 2]


def test_data_040_failed_migration_rolls_back(tmp_path):
    (tmp_path / "0001_bad.sql").write_text(
        "CREATE TABLE half (id INTEGER PRIMARY KEY); INSERT INTO missing VALUES (1);"
    )
    conn = connect(tmp_path / "t.db")
    with pytest.raises(sqlite3.OperationalError):
        migrate(conn, tmp_path)
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "half" not in tables
    assert conn.execute("SELECT count(*) FROM schema_migration").fetchone()[0] == 0


@pytest.mark.parametrize("name", ["1_short.sql", "0001-dash.sql", "0001_Upper.sql"])
def test_eng_050_rejects_badly_named_migrations(tmp_path, name):
    (tmp_path / name).write_text("SELECT 1;")
    with pytest.raises(DatabaseError):
        migrate(connect(tmp_path / "t.db"), tmp_path)


def test_eng_050_rejects_two_migrations_with_one_number(tmp_path):
    (tmp_path / "0001_a.sql").write_text("SELECT 1;")
    (tmp_path / "0001_b.sql").write_text("SELECT 1;")
    with pytest.raises(DatabaseError):
        migrate(connect(tmp_path / "t.db"), tmp_path)


def test_eng_050_stops_when_a_recorded_number_has_a_different_file(tmp_path):
    # Issue #55: a preview ran 0002_old, then it was renumbered to 0003 and a new 0002 merged.
    (tmp_path / "0001_first.sql").write_text(
        "CREATE TABLE first (id INTEGER PRIMARY KEY);"
    )
    (tmp_path / "0002_old.sql").write_text("CREATE TABLE old (id INTEGER PRIMARY KEY);")
    conn = connect(tmp_path / "t.db")
    migrate(conn, tmp_path)
    (tmp_path / "0002_old.sql").rename(tmp_path / "0003_old.sql")
    (tmp_path / "0002_new.sql").write_text("CREATE TABLE new (id INTEGER PRIMARY KEY);")
    with pytest.raises(DatabaseError, match=r"0002_old\.sql.*0002_new\.sql"):
        migrate(conn, tmp_path)
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "new" not in tables


def test_data_005_foreign_keys_on(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        _add_player(conn, church_id=999)


def test_arch_001_wal_mode(conn):
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_data_011_player_has_only_listed_fields(conn):
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(player)")}
    assert columns == {
        "id",
        "public_id",
        "first_name",
        "last_name",
        "church_id",
        "is_under_18",
        "pin_hash",
        "failed_pin_attempts",
        "locked_at",
        "created_at",
    }


def test_data_002_no_email_or_phone_columns(conn):
    for table in ("church", "player"):
        columns = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        assert not {c for c in columns if "email" in c or "phone" in c}


def test_data_003_public_id_unique(conn):
    church = _add_church(conn)
    _add_player(conn, church, first="Test", public_id="same")
    with pytest.raises(sqlite3.IntegrityError):
        _add_player(conn, church, first="Other", public_id="same")


def test_safe_002_church_name_unique(conn):
    _add_church(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _add_church(conn)


def test_data_016_same_full_name_same_church_refused_ignoring_case(conn):
    church = _add_church(conn)
    _add_player(conn, church, first="Test", last="Player 1", public_id="pub-1")
    with pytest.raises(sqlite3.IntegrityError):
        _add_player(conn, church, first="TEST", last="player 1", public_id="pub-2")


def test_data_016_same_full_name_other_church_allowed(conn):
    _add_player(conn, _add_church(conn, "Example Church A"), public_id="pub-1")
    _add_player(conn, _add_church(conn, "Example Church B"), public_id="pub-2")


@pytest.mark.parametrize("first", ["", " Test", "Test "])
def test_data_016_names_must_be_trimmed_and_not_empty(conn, first):
    with pytest.raises(sqlite3.IntegrityError):
        _add_player(conn, _add_church(conn), first=first)


def test_data_004_created_at_is_utc(conn):
    _add_player(conn, _add_church(conn))
    created = conn.execute("SELECT created_at FROM player").fetchone()[0]
    assert created.endswith("Z")


def test_data_040_app_start_runs_migrations(tmp_path, monkeypatch):
    path = tmp_path / "start.db"
    monkeypatch.setenv("SQ_DB_PATH", str(path))
    with TestClient(create_app()):
        pass
    conn = connect(path)
    assert conn.execute("SELECT name FROM schema_migration").fetchone()[0] == (
        "0001_create_church_and_player.sql"
    )


def test_arch_010_db_path_required(monkeypatch):
    monkeypatch.delenv("SQ_DB_PATH", raising=False)
    with pytest.raises(DatabaseError):
        db_path_from_env()


def test_data_003_existing_takeaways_get_a_public_id_and_keep_their_data(tmp_path):
    # journal.share-review: 0011 rebuilds the takeaway table, so notes saved before it must survive.
    old = tmp_path / "old"
    old.mkdir()
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if int(path.name[:4]) <= 10:
            (old / path.name).write_text(path.read_text())
    conn = connect(tmp_path / "t.db")
    migrate(conn, old)
    player = _add_player(conn, _add_church(conn))
    session = conn.execute(
        "INSERT INTO session (public_id, title, ended_at)"
        " VALUES ('pub-s1', 'Example Session 1', '2027-03-05T10:00:00Z')"
    ).lastrowid
    conn.executemany(
        "INSERT INTO takeaway (player_id, session_id, text) VALUES (?, ?, ?)",
        [
            (player, session, "Example takeaway one"),
            (player, session, "Example takeaway two"),
        ],
    )
    assert migrate(conn) == ["0011_add_takeaway_public_id.sql"]
    rows = conn.execute(
        "SELECT id, public_id, text, visibility, review_status FROM takeaway ORDER BY id"
    ).fetchall()
    assert [(r["text"], r["visibility"], r["review_status"]) for r in rows] == [
        ("Example takeaway one", "private", "not_needed"),
        ("Example takeaway two", "private", "not_needed"),
    ]
    assert len({r["public_id"] for r in rows}) == 2
    assert all(r["public_id"] for r in rows)
