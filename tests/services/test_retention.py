import re
import shutil
import sqlite3
from datetime import date, timedelta

import pytest

from app.auth.session import MAX_AGE_SECONDS
from app.config import load_config
from app.db import MIGRATIONS_DIR, connect, migrate
from app.services import retention
from app.services.audit import record
from app.services.retention import (
    DELETE_TABLES,
    KEEP_TABLES,
    MANUAL_STEPS,
    RetentionError,
    as_of_allowed,
    retention_date,
    run,
)

FAKE_PIN_HASH = "not-a-real-hash-zq7"  # fake data (ENG-047), easy to spot in raw bytes

# Columns that hold a player's id, with or without a foreign key (audit_log has none).
PLAYER_ID_COLUMN = re.compile(r"player|^actor_id$|^target_id$")


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
    conn.execute(
        "INSERT INTO point_ledger (player_id, amount, reason_code, source_type, source_id)"
        " VALUES (?, 1, 'test_award', 'connection', ?)",
        (players[0], connection),
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


@pytest.fixture
def local_command(filled, db_path, monkeypatch):
    """Runs the command against the filled test database, as on a laptop (no Railway)."""
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    for name in ("RAILWAY_ENVIRONMENT_NAME", "RAILWAY_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    return retention.main


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


def _player_id_columns(conn, table):
    return {
        r["name"]
        for r in conn.execute(f"PRAGMA table_info({table})")
        if PLAYER_ID_COLUMN.search(r["name"])
    }


def _raw_bytes(db_path):
    files = [db_path, db_path.with_name(db_path.name + "-wal")]
    return b"".join(p.read_bytes() for p in files if p.exists())


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
    assert removed == {
        "audit_log": 1,
        "church_met": 1,
        "connection": 1,
        "point_ledger": 1,
        "player": 2,
    }
    for table in ("player", "connection", "church_met", "point_ledger"):
        assert _count(filled, table) == 0
    assert _count(filled, "church") == 2  # kept: not personal data


def test_safe_014_deleted_data_is_gone_from_the_raw_files(filled, db_path, cfg):
    # A plain DELETE leaves the bytes in free pages and the -wal file, where a tool could read them.
    secrets = (b"Player 1", b"Player 2", b"pub-1", FAKE_PIN_HASH.encode())
    assert all(s in _raw_bytes(db_path) for s in secrets)  # the check can see them
    run(filled, retention_date(cfg), cfg)
    raw = _raw_bytes(db_path)
    for secret in secrets:
        assert secret not in raw, secret


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


def test_data_015_missing_trigger_stops_with_a_clear_error(filled, cfg):
    filled.execute("DROP TRIGGER audit_log_no_delete")
    with pytest.raises(RetentionError, match="trigger is missing"):
        run(filled, retention_date(cfg), cfg)
    assert _count(filled, "player") == 2


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
    linked = {"player"} | {t for t in tables if _player_id_columns(conn, t)}
    while True:
        more = {t for t in tables - linked if _references(conn, t) & linked}
        if not more:
            break
        linked |= more
    assert linked <= set(DELETE_TABLES)


def test_safe_014_kept_tables_hold_no_player_ids(conn):
    # Catches a player id stored without a foreign key, the way audit_log stores actor_id.
    for table in KEEP_TABLES:
        assert not _player_id_columns(conn, table), table


def test_safe_014_delete_order_puts_children_first(conn):
    # A table that points to another must be emptied first, or the foreign key refuses the delete.
    for i, table in enumerate(DELETE_TABLES):
        for later in DELETE_TABLES[i + 1 :]:
            assert table not in _references(conn, later), (
                f"{later} must come before {table}"
            )


def test_safe_014_command_without_confirm_removes_nothing(
    local_command, filled, cfg, capsys
):
    assert local_command(["--as-of", retention_date(cfg).isoformat()]) == 0
    assert "Would remove 2 rows from player" in capsys.readouterr().out
    assert _count(filled, "player") == 2


def test_safe_014_command_confirm_deletes_and_lists_manual_steps(
    local_command, filled, cfg, capsys
):
    assert local_command(["--confirm", "--as-of", retention_date(cfg).isoformat()]) == 0
    out = capsys.readouterr().out
    assert "Removed 2 rows from player" in out
    for step in MANUAL_STEPS:
        assert step in out
    assert _count(filled, "player") == 0


def test_ops_042_manual_steps_cover_backups_logs_data_folder_and_staff():
    text = " ".join(MANUAL_STEPS)
    for rule in ("ARCH-052", "ARCH-053", "OPS-042"):
        assert rule in text
    assert "staff account" in text and "logs" in text and "backups" in text


def test_safe_014_command_refuses_early_date(local_command, filled, cfg):
    early = (retention_date(cfg) - timedelta(days=1)).isoformat()
    assert local_command(["--confirm", "--as-of", early]) == 1
    assert _count(filled, "player") == 2


def test_data_040_command_never_migrates(tmp_path, monkeypatch, cfg, capsys):
    # A database one migration behind the code is refused, and left exactly as it was.
    old = tmp_path / "old-migrations"
    old.mkdir()
    shutil.copy(MIGRATIONS_DIR / "0001_create_church_and_player.sql", old)
    path = tmp_path / "behind.db"
    db = connect(path)
    migrate(db, old)
    db.close()
    monkeypatch.setenv("SQ_DB_PATH", str(path))
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    assert retention.main(["--as-of", retention_date(cfg).isoformat()]) == 1
    assert "does not match this code" in capsys.readouterr().err
    db = connect(path)
    assert [r["name"] for r in db.execute("SELECT name FROM schema_migration")] == [
        "0001_create_church_and_player.sql"
    ]
    db.close()


def test_safe_014_command_refuses_a_missing_database(tmp_path, monkeypatch):
    path = tmp_path / "nowhere.db"
    monkeypatch.setenv("SQ_DB_PATH", str(path))
    assert retention.main([]) == 1
    assert not path.exists()


@pytest.mark.parametrize(
    "environment, allowed",
    [
        (None, True),
        ("staging", True),
        ("side-quest-pr-52", True),
        ("production", False),
        ("something-else", False),
    ],
)
def test_safe_014_as_of_only_where_data_is_fake(environment, allowed):
    assert as_of_allowed(environment) is allowed


def test_safe_014_as_of_refused_on_production(filled, db_path, cfg, monkeypatch):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    assert (
        retention.main(["--confirm", "--as-of", retention_date(cfg).isoformat()]) == 2
    )
    assert _count(filled, "player") == 2


def test_arch_034_session_cookie_outlasts_wrapped(cfg):
    # WRAP-004: Wrapped closes on the keep-until date, counted from the last day of the event.
    end = date.fromisoformat(cfg["event"]["end_date"])
    assert timedelta(seconds=MAX_AGE_SECONDS) >= retention_date(cfg) - end
