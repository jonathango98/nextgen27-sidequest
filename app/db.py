"""SQLite connections and the migration runner (ARCH-001, DATA-040, ENG-050)."""

import os
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Request

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")

# ARCH-013: one writer at a time, so other writers wait instead of failing at once.
BUSY_TIMEOUT_MS = 5000


class DatabaseError(Exception):
    pass


def db_path_from_env() -> Path:
    # ARCH-010: the file sits on the Railway volume. No default, so it never lands on throwaway disk.
    value = os.environ.get("SQ_DB_PATH")
    if not value:
        raise DatabaseError("SQ_DB_PATH is not set")
    return Path(value)


def connect(path: Path) -> sqlite3.Connection:
    # FastAPI may open a connection in one worker thread and use it in another, never both at once.
    conn = sqlite3.connect(path, autocommit=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # DATA-005
    conn.execute("PRAGMA journal_mode = WAL")  # ARCH-001
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    return conn


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request."""
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def _migration_files(migrations_dir: Path) -> list[tuple[int, Path]]:
    found: dict[int, Path] = {}
    for path in migrations_dir.glob("*.sql"):
        match = MIGRATION_NAME.match(path.name)
        if not match:
            raise DatabaseError(
                f"Migration file name is not NNNN_name.sql: {path.name}"
            )
        number = int(match.group(1))
        if number in found:
            raise DatabaseError(f"Two migrations numbered {number:04d}")
        found[number] = path
    return sorted(found.items())


def migrate(
    conn: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR
) -> list[str]:
    """Apply migrations not yet applied, in order. Returns the names applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migration ("
        " version INTEGER PRIMARY KEY,"
        " name TEXT NOT NULL,"
        " applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))"
        ") STRICT"
    )
    done = {
        row["version"] for row in conn.execute("SELECT version FROM schema_migration")
    }
    applied = []
    for number, path in _migration_files(migrations_dir):
        if number in done:
            continue
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.executescript(path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migration (version, name) VALUES (?, ?)",
                (number, path.name),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        applied.append(path.name)
    return applied
