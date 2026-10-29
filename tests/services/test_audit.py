import re
import sqlite3

import pytest

from app.db import connect, migrate
from app.services.audit import AuditError, record


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


def _row(conn, row_id):
    return conn.execute("SELECT * FROM audit_log WHERE id = ?", (row_id,)).fetchone()


def test_arch_050_record_saves_who_what_target_reason_and_when(conn):
    row_id = record(
        conn,
        actor_type="admin",
        actor_id=7,
        action="pin_reset",
        target_type="player",
        target_id=42,
        reason="Checked badge at the game booth",
    )
    row = _row(conn, row_id)
    assert (row["actor_type"], row["actor_id"]) == ("admin", 7)
    assert row["action"] == "pin_reset"
    assert (row["target_type"], row["target_id"]) == ("player", 42)
    assert row["reason"] == "Checked badge at the game booth"
    assert row["created_at"]


def test_arch_050_system_action_has_no_actor_id(conn):
    row = _row(
        conn, record(conn, actor_type="system", actor_id=None, action="checkin_open")
    )
    assert row["actor_id"] is None
    assert row["target_type"] is None and row["reason"] is None


def test_arch_050_record_rolls_back_with_the_callers_transaction(conn):
    conn.execute("BEGIN IMMEDIATE")
    record(conn, actor_type="admin", actor_id=1, action="pause")
    conn.execute("ROLLBACK")
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0


def test_data_015_audit_row_cannot_be_updated(conn):
    row_id = record(conn, actor_type="admin", actor_id=1, action="pause")
    with pytest.raises(sqlite3.IntegrityError, match="never updated"):
        conn.execute("UPDATE audit_log SET action = 'resume' WHERE id = ?", (row_id,))
    assert _row(conn, row_id)["action"] == "pause"


def test_data_015_audit_row_cannot_be_deleted(conn):
    row_id = record(conn, actor_type="admin", actor_id=1, action="pause")
    with pytest.raises(sqlite3.IntegrityError, match="never deleted"):
        conn.execute("DELETE FROM audit_log WHERE id = ?", (row_id,))
    assert _row(conn, row_id) is not None


def test_data_015_audit_row_cannot_be_replaced(conn):
    row_id = record(conn, actor_type="admin", actor_id=1, action="pause")
    with pytest.raises(sqlite3.IntegrityError, match="never replaced"):
        conn.execute(
            "INSERT OR REPLACE INTO audit_log (id, actor_type, actor_id, action)"
            " VALUES (?, 'admin', 1, 'resume')",
            (row_id,),
        )
    assert _row(conn, row_id)["action"] == "pause"


def test_safe_014_retention_can_delete_inside_one_transaction(conn):
    record(conn, actor_type="admin", actor_id=1, action="pause")
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'audit_log_no_delete'"
    ).fetchone()["sql"]
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DROP TRIGGER audit_log_no_delete")
    conn.execute("DELETE FROM audit_log")
    conn.execute(sql)
    conn.execute("COMMIT")
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0
    row_id = record(conn, actor_type="admin", actor_id=1, action="resume")
    with pytest.raises(sqlite3.IntegrityError, match="never deleted"):
        conn.execute("DELETE FROM audit_log WHERE id = ?", (row_id,))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"actor_type": "hacker", "actor_id": 1, "action": "pause"},
        {"actor_type": "admin", "actor_id": None, "action": "pause"},
        {"actor_type": "system", "actor_id": 1, "action": "pause"},
        {"actor_type": "admin", "actor_id": 1, "action": "Reset PIN for Test Player 1"},
        {"actor_type": "admin", "actor_id": 1, "action": ""},
        {
            "actor_type": "admin",
            "actor_id": 1,
            "action": "pause",
            "target_type": "player",
        },
        {"actor_type": "admin", "actor_id": "Test Player 1", "action": "pause"},
        {
            "actor_type": "admin",
            "actor_id": 1,
            "action": "pause",
            "target_type": "Test Player 1",
            "target_id": 1,
        },
    ],
)
def test_arch_051_record_refuses_names_and_free_text_outside_reason(conn, kwargs):
    with pytest.raises(AuditError):
        record(conn, **kwargs)
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0


def test_arch_051_database_refuses_free_text_action_too(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO audit_log (actor_type, actor_id, action) VALUES ('admin', 1, ?)",
            ("PIN is 1234",),
        )


def test_data_004_created_at_is_utc(conn):
    row = _row(conn, record(conn, actor_type="admin", actor_id=1, action="pause"))
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", row["created_at"])
