import sqlite3
from datetime import date, timedelta

import pytest

from app.config import load_config
from app.db import connect, migrate
from app.services import retention
from app.services.audit import record
from app.services.retention import (
    DELETE_TABLES,
    KEEP_TABLES,
    RetentionError,
    retention_date,
    run,
)

FAKE_PIN_HASH = "not-a-real-hash"  # fake data (ENG-047)


@pytest.fixture
def cfg():
    return load_config()


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
def filled(conn):
    churches = [
        conn.execute("INSERT INTO church (name) VALUES (?)", (name,)).lastrowid
        for name in ("Example Church A", "Example Church B")
    ]
    players = [
        conn.execute(
            "INSERT INTO player"
            " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " VALUES (?, 'Test', ?, ?, 0, ?)",
            (f"pub-{n}", f"Player {n}", church, FAKE_PIN_HASH),
        ).lastrowid
        for n, church in ((1, churches[0]), (2, churches[1]))
    ]
    connection = conn.execute(
        "INSERT INTO connection (player_low_id, player_high_id, scanner_id, is_same_church)"
        " VALUES (?, ?, ?, 0)",
        (players[0], players[1], players[0]),
    ).lastrowid
    conn.execute(
        "INSERT INTO church_met (player_id, church_id, connection_id) VALUES (?, ?, ?)",
        (players[0], churches[1], connection),
    )
    record(
        conn,
        actor_type="admin",
        actor_id=1,
        action="pin_reset",
        target_type="player",
        target_id=1,
    )
    return conn


def _count(conn, table):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def _tables(conn):
    return {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _references(conn, table):
    return {r["table"] for r in conn.execute(f"PRAGMA foreign_key_list({table})")}


def test_safe_014_keep_until_counts_from_event_end_date(cfg):
    end = date.fromisoformat(cfg["event"]["end_date"])
    assert retention_date(cfg) == end + timedelta(
        days=cfg["data"]["retention_days_after_event"]
    )


def test_safe_014_cleanup_refuses_before_retention_date(filled, cfg):
    with pytest.raises(RetentionError, match="kept until"):
        run(filled, retention_date(cfg) - timedelta(days=1), cfg)
    assert _count(filled, "player") == 2
    assert _count(filled, "audit_log") == 1


def test_safe_014_cleanup_deletes_player_data_on_the_date(filled, cfg):
    removed = run(filled, retention_date(cfg), cfg)
    assert removed == {"audit_log": 1, "church_met": 1, "connection": 1, "player": 2}
    for table in ("player", "connection", "church_met"):
        assert _count(filled, table) == 0
    assert _count(filled, "church") == 2  # kept: not personal data


def test_safe_014_only_an_unlinked_cleanup_note_stays(filled, cfg):
    run(filled, retention_date(cfg), cfg)
    rows = filled.execute("SELECT * FROM audit_log").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert (row["actor_type"], row["action"]) == ("system", "retention_cleanup")
    assert row["actor_id"] is None and row["target_id"] is None


def test_safe_014_second_run_keeps_the_first_cleanup_note(filled, cfg):
    run(filled, retention_date(cfg), cfg)
    removed = run(filled, retention_date(cfg) + timedelta(days=1), cfg)
    assert removed["audit_log"] == 0
    notes = filled.execute(
        "SELECT count(*) FROM audit_log WHERE action = 'retention_cleanup'"
    ).fetchone()[0]
    assert notes == 2


def test_data_015_audit_triggers_are_back_after_cleanup(filled, cfg):
    run(filled, retention_date(cfg), cfg)
    row_id = record(filled, actor_type="admin", actor_id=1, action="pause")
    with pytest.raises(sqlite3.IntegrityError, match="never deleted"):
        filled.execute("DELETE FROM audit_log WHERE id = ?", (row_id,))


def test_safe_014_cleanup_is_all_or_nothing(filled, cfg, monkeypatch):
    # Fails after every real table is emptied, so everything must come back.
    monkeypatch.setattr(retention, "DELETE_TABLES", (*DELETE_TABLES, "missing_table"))
    with pytest.raises(sqlite3.OperationalError):
        run(filled, retention_date(cfg), cfg)
    assert _count(filled, "player") == 2
    assert _count(filled, "connection") == 1
    assert _count(filled, "audit_log") == 1
    with pytest.raises(sqlite3.IntegrityError, match="never deleted"):
        filled.execute("DELETE FROM audit_log")


def test_safe_014_every_table_is_deleted_or_kept_on_purpose(conn):
    # A new table fails here until someone adds it to DELETE_TABLES or KEEP_TABLES.
    assert not set(DELETE_TABLES) & set(KEEP_TABLES)
    assert _tables(conn) == set(DELETE_TABLES) | set(KEEP_TABLES)


def test_safe_014_tables_linked_to_players_are_deleted(conn):
    tables = _tables(conn)
    linked = {"player"}
    while True:
        more = {t for t in tables - linked if _references(conn, t) & linked}
        if not more:
            break
        linked |= more
    assert linked <= set(DELETE_TABLES)
    assert (
        "audit_log" in DELETE_TABLES
    )  # points to players by id, without a foreign key


def test_safe_014_delete_order_puts_children_first(conn):
    # A table that points to another must be emptied first, or the foreign key refuses the delete.
    for i, table in enumerate(DELETE_TABLES):
        for later in DELETE_TABLES[i + 1 :]:
            assert table not in _references(conn, later), (
                f"{later} must come before {table}"
            )


def test_safe_014_command_without_confirm_removes_nothing(
    filled, db_path, cfg, monkeypatch, capsys
):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    for name in ("RAILWAY_ENVIRONMENT_NAME", "RAILWAY_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    as_of = retention_date(cfg).isoformat()
    assert retention.main(["--as-of", as_of]) == 0
    assert "Would remove 2 rows from player" in capsys.readouterr().out
    assert _count(filled, "player") == 2


def test_safe_014_command_confirm_deletes_on_a_local_copy(
    filled, db_path, cfg, monkeypatch, capsys
):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    for name in ("RAILWAY_ENVIRONMENT_NAME", "RAILWAY_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    as_of = retention_date(cfg).isoformat()
    assert retention.main(["--confirm", "--as-of", as_of]) == 0
    assert "Removed 2 rows from player" in capsys.readouterr().out
    assert _count(filled, "player") == 0


def test_safe_014_command_refuses_early_date(filled, db_path, cfg, monkeypatch):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    early = (retention_date(cfg) - timedelta(days=1)).isoformat()
    assert retention.main(["--confirm", "--as-of", early]) == 1
    assert _count(filled, "player") == 2


def test_safe_014_as_of_refused_on_railway(filled, db_path, cfg, monkeypatch):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    as_of = retention_date(cfg).isoformat()
    assert retention.main(["--confirm", "--as-of", as_of]) == 2
    assert _count(filled, "player") == 2
