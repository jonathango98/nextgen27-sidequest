"""Deletes every player-linked record once the keep-until date has passed (SAFE-014, ARCH-052).

Usage: python -m app.services.retention [--confirm] [--as-of YYYY-MM-DD]

Without --confirm it only reports what it would remove. --as-of pretends today is a later date,
for trying it on a local copy, and is refused on Railway so production is never wiped early.
Railway backups and the real data folder are cleared by hand (ARCH-053, OPS-042).
"""

import argparse
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import load_config
from app.db import connect, db_path_from_env, migrate
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
}

AUDIT_NO_DELETE_TRIGGER = "audit_log_no_delete"


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


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: conn.execute(f"SELECT count(*) FROM {table}{_where(table)}").fetchone()[
            0
        ]
        for table in DELETE_TABLES
    }


def run(conn: sqlite3.Connection, today: date, cfg: dict) -> dict[str, int]:
    """Delete every player-linked row in one transaction. Returns rows removed per table."""
    keep_until = retention_date(cfg)
    if today < keep_until:
        raise RetentionError(
            f"Nothing removed: player data is kept until {keep_until.isoformat()}"
        )
    conn.execute("BEGIN IMMEDIATE")
    try:
        # DATA-015: the only place audit rows are deleted. The trigger is back before COMMIT.
        trigger_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (AUDIT_NO_DELETE_TRIGGER,),
        ).fetchone()["sql"]
        conn.execute(f"DROP TRIGGER {AUDIT_NO_DELETE_TRIGGER}")
        removed = {
            table: conn.execute(f"DELETE FROM {table}{_where(table)}").rowcount
            for table in DELETE_TABLES
        }
        conn.execute(trigger_sql)
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
    return removed


def on_railway() -> bool:
    return bool(
        os.environ.get("RAILWAY_ENVIRONMENT_NAME")
        or os.environ.get("RAILWAY_ENVIRONMENT")
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.services.retention")
    parser.add_argument("--confirm", action="store_true", help="really delete")
    parser.add_argument(
        "--as-of", type=date.fromisoformat, help="pretend date, local only"
    )
    args = parser.parse_args(argv)

    if args.as_of and on_railway():
        print("Nothing removed: --as-of is for local copies only", file=sys.stderr)
        return 2
    cfg = load_config()
    today = args.as_of or venue_today(cfg)
    conn = connect(db_path_from_env())
    try:
        migrate(conn)
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
    print(
        "Also clear Railway backups and the real data folder by hand (ARCH-053, OPS-042)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
