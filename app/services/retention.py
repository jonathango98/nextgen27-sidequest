"""Deletes every player-linked record once the keep-until date has passed (SAFE-014, ARCH-052).

Usage: python -m app.services.retention [--confirm] [--as-of YYYY-MM-DD]

Without --confirm it only reports what it would remove, and it never changes the schema.
--as-of pretends today is a later date. It works on a local copy, staging, and PR previews,
and is refused on production so real data is never wiped early.
"""

import argparse
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import load_config
from app.db import MIGRATIONS_DIR, connect, db_path_from_env
from app.services import churches
from app.services.audit import record

# Every table holding player-linked data, children before the tables they point to.
DELETE_TABLES = ("audit_log", "church_met", "connection", "player")

# Earlier cleanup notes hold totals only, with no link to a person, so later runs keep them.
KEEP_ROWS = {"audit_log": "action <> 'retention_cleanup'"}

# Tables that survive, and why. Nothing in them links to a person.
KEEP_TABLES = {
    "church": "the public church list, not personal data",
    "game_state": "the one-row game switch. updated_by is a staff id, not a player (OPS-042)",
    "schema_migration": "bookkeeping for the migration runner",
    "staff_account": "usher and admin accounts, not players. Switched off by hand (OPS-042)",
}

AUDIT_NO_DELETE_TRIGGER = "audit_log_no_delete"

# Done by hand on the same date. The command can't reach these (ARCH-052, ARCH-053, OPS-042).
MANUAL_STEPS = (
    "Delete the Railway volume backups (ARCH-053).",
    "Delete the server logs on Railway (ARCH-052).",
    "Delete the real event data folder (OPS-042).",
    "Switch off every staff account (OPS-042).",
)

# Where --as-of may pretend a date. Production and unknown Railway environments are refused.
AS_OF_ENVIRONMENTS = {"staging"}


class RetentionError(Exception):
    pass


def retention_date(cfg: dict) -> date:
    end_date = cfg["event"]["end_date"]
    if not end_date:
        raise RetentionError("event.end_date is not set in game-config.yaml")
    days = cfg["data"]["retention_days_after_event"]
    return date.fromisoformat(end_date) + timedelta(days=days)


def venue_today(cfg: dict) -> date:
    return datetime.now(ZoneInfo(cfg["game"]["timezone"])).date()  # GAME-105


def _where(table: str) -> str:
    return f" WHERE {KEEP_ROWS[table]}" if table in KEEP_ROWS else ""


def check_schema(
    conn: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR
) -> None:
    """Refuse unless the database has exactly this code's migrations. Never migrates."""
    try:
        applied = {r["name"] for r in conn.execute("SELECT name FROM schema_migration")}
    except sqlite3.OperationalError:
        raise RetentionError(
            "This database has no migrations. Check SQ_DB_PATH."
        ) from None
    if applied != {p.name for p in migrations_dir.glob("*.sql")}:
        raise RetentionError(
            "Nothing removed: the database schema does not match this code. "
            "Deploy this code first, then run the cleanup from the deployed app."
        )


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: conn.execute(f"SELECT count(*) FROM {table}{_where(table)}").fetchone()[
            0
        ]
        for table in DELETE_TABLES
    }


def run(conn: sqlite3.Connection, today: date, cfg: dict) -> dict[str, int]:
    """Delete every player-linked row in one transaction, then scrub the file. Returns counts."""
    keep_until = retention_date(cfg)
    if today < keep_until:
        raise RetentionError(
            f"Nothing removed: player data is kept until {keep_until.isoformat()}"
        )
    # SAFE-014: a plain DELETE leaves the old bytes in free pages, so overwrite them with zeros.
    conn.execute("PRAGMA secure_delete = ON")
    conn.execute("BEGIN IMMEDIATE")
    try:
        trigger = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (AUDIT_NO_DELETE_TRIGGER,),
        ).fetchone()
        if trigger is None:
            raise RetentionError(
                f"Nothing removed: the {AUDIT_NO_DELETE_TRIGGER} trigger is missing, so the "
                "audit log is not write-protected (DATA-015). Check the database first."
            )
        # DATA-015: the only place audit rows are deleted. The trigger is back before COMMIT.
        conn.execute(f"DROP TRIGGER {AUDIT_NO_DELETE_TRIGGER}")
        removed = {
            table: conn.execute(f"DELETE FROM {table}{_where(table)}").rowcount
            for table in DELETE_TABLES
        }
        conn.execute(trigger["sql"])
        # Only totals with no link to a person stay (SAFE-014).
        record(
            conn,
            actor_type="system",
            actor_id=None,
            action="retention_cleanup",
            reason=", ".join(f"{t} {n}" for t, n in removed.items()),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _scrub(conn)
    return removed


def _scrub(conn: sqlite3.Connection) -> None:
    # Rebuild the file and empty the -wal file, which can still hold older copies of the rows.
    conn.execute("VACUUM")
    busy = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]
    if busy:
        raise RetentionError(
            "Rows were deleted, but the -wal file may still hold old copies because another "
            "process has the database open. Stop the app and run the command again."
        )


def railway_environment() -> str | None:
    return os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get(
        "RAILWAY_ENVIRONMENT"
    )


def as_of_allowed(environment: str | None) -> bool:
    if environment is None:
        return True  # a local copy
    return environment in AS_OF_ENVIRONMENTS or churches.is_preview(environment)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.services.retention")
    parser.add_argument("--confirm", action="store_true", help="really delete")
    parser.add_argument(
        "--as-of", type=date.fromisoformat, help="pretend date, never on production"
    )
    args = parser.parse_args(argv)

    if args.as_of and not as_of_allowed(railway_environment()):
        print("Nothing removed: --as-of is refused on production", file=sys.stderr)
        return 2
    path = db_path_from_env()
    if not path.exists():
        print(f"Nothing removed: no database at {path}", file=sys.stderr)
        return 1
    cfg = load_config()
    today = args.as_of or venue_today(cfg)
    conn = connect(path)
    try:
        check_schema(conn)
        if not args.confirm:
            keep_until = retention_date(cfg)
            print(
                f"Keep-until date: {keep_until.isoformat()}. Today: {today.isoformat()}."
            )
            for table, n in counts(conn).items():
                print(f"Would remove {n} rows from {table}.")
            print("Nothing removed. Add --confirm to delete.")
            return 0
        removed = run(conn, today, cfg)
    except RetentionError as error:
        print(error, file=sys.stderr)
        return 1
    finally:
        conn.close()
    for table, n in removed.items():
        print(f"Removed {n} rows from {table}.")
    print("Now do these by hand on the same day:")
    for step in MANUAL_STEPS:
        print(f"- {step}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
