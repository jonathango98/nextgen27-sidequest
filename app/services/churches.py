"""The church list players pick from at sign-up (SAFE-002, DEC-011).

Loaded from a CSV kept outside the repo, then fixed by admins on /admin/churches (GAME-110).

Usage: python -m app.services.churches <file.csv>   (or "-" to read from stdin)

The CSV has one column, "name". Region is not loaded while DATA-010 is OPEN.
The real list is real event data, so it never goes in the repo (SAFE-030, ARCH-007).
"""

import csv
import io
import re
import sqlite3
import sys
from dataclasses import dataclass

from app.db import connect, db_path_from_env, migrate
from app.services import audit

HEADER = ["name"]
# Not a game number: the longest name the admin form takes, so a pasted paragraph can't fill
# the sign-up list. The same limit as a session title.
NAME_MAX_CHARS = 120

# Railway names each PR preview environment "<project>-pr-<number>" (ARCH-017).
# Staging and production never match.
PREVIEW_ENV = re.compile(r"-pr-\d+$")
# Obviously fake (SAFE-031), so a preview can be tested without the real list.
EXAMPLE_CHURCHES = ["Example Church A", "Example Church B", "Example Church C"]


class ChurchListError(Exception):
    pass


class ChurchNotFound(Exception):
    pass


@dataclass(frozen=True)
class Church:
    id: int
    name: str


def _key(name: str) -> str:
    return " ".join(name.split()).casefold()


def parse(text: str) -> list[str]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or [c.strip().lower() for c in rows[0]] != HEADER:
        raise ChurchListError("The first row must be exactly: name")
    names = []
    for line, row in enumerate(rows[1:], start=2):
        if len(row) > 1:
            raise ChurchListError(f"Row {line} has more than one column")
        name = row[0].strip() if row else ""
        if name:
            names.append(name)
    return names


def load(conn: sqlite3.Connection, names: list[str]) -> list[str]:
    """Add churches not already in the table. Returns the names added. All or nothing."""
    seen: dict[str, str] = {}
    for name in names:
        other = seen.get(_key(name))
        if other is not None and other != name:
            raise ChurchListError(f'"{name}" and "{other}" look like the same church')
        seen[_key(name)] = name

    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = {
            _key(r["name"]): r["name"] for r in conn.execute("SELECT name FROM church")
        }
        added = []
        for key, name in seen.items():
            if key in existing:
                if existing[key] != name:
                    raise ChurchListError(
                        f'"{name}" looks like "{existing[key]}", which is already loaded'
                    )
                continue
            conn.execute("INSERT INTO church (name) VALUES (?)", (name,))
            added.append(name)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return added


def list_all(conn: sqlite3.Connection) -> list[Church]:
    rows = conn.execute("SELECT id, name FROM church ORDER BY name COLLATE NOCASE")
    return [Church(r["id"], r["name"]) for r in rows]


def _clean_name(name: str) -> str:
    name = " ".join(name.split())
    if not name:
        raise ChurchListError("Please type the church's name.")
    if len(name) > NAME_MAX_CHARS:
        raise ChurchListError(f"Church names can be up to {NAME_MAX_CHARS} characters.")
    return name


def _refuse_look_alike(conn: sqlite3.Connection, name: str, church_id: int | None):
    for row in conn.execute("SELECT id, name FROM church"):
        if row["id"] != church_id and _key(row["name"]) == _key(name):
            raise ChurchListError(
                f'"{name}" looks like "{row["name"]}", which is already in the list.'
            )


def _audit(conn: sqlite3.Connection, admin_id: int, action: str, church_id: int):
    audit.record(
        conn,
        actor_type="admin",
        actor_id=admin_id,
        action=action,
        target_type="church",
        target_id=church_id,
    )


def add_church(conn: sqlite3.Connection, name: str, admin_id: int) -> int:
    """An admin adds a church to the sign-up list (SAFE-002, GAME-110), with an audit row (ARCH-050)."""
    name = _clean_name(name)
    conn.execute("BEGIN IMMEDIATE")
    try:
        _refuse_look_alike(conn, name, None)
        church_id = conn.execute(
            "INSERT INTO church (name) VALUES (?)", (name,)
        ).lastrowid
        _audit(conn, admin_id, "church_add", church_id)
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return church_id


def rename_church(
    conn: sqlite3.Connection, church_id: int, name: str, admin_id: int
) -> bool:
    """Fix a church's name. Returns whether anything changed.

    The church keeps its id, so its players, the new church bonus (GAME-011, GAME-018) and the
    church leaderboard stay the same.
    """
    name = _clean_name(name)
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT name FROM church WHERE id = ?", (church_id,)
        ).fetchone()
        if row is None:
            raise ChurchNotFound
        if row["name"] == name:
            conn.execute("ROLLBACK")
            return False
        _refuse_look_alike(conn, name, church_id)
        conn.execute("UPDATE church SET name = ? WHERE id = ?", (name, church_id))
        _audit(conn, admin_id, "church_rename", church_id)
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return True


def is_preview(environment_name: str | None) -> bool:
    return bool(environment_name and PREVIEW_ENV.search(environment_name))


def seed_examples(conn: sqlite3.Connection) -> list[str]:
    """A PR preview starts with no churches, so nobody can join. Adds fake ones only if empty."""
    if conn.execute("SELECT 1 FROM church LIMIT 1").fetchone():
        return []
    return load(conn, EXAMPLE_CHURCHES)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    source = argv[0]
    if source == "-":
        text = sys.stdin.read()
    else:
        with open(source, encoding="utf-8-sig", newline="") as f:
            text = f.read()
    conn = connect(db_path_from_env())
    try:
        migrate(conn)
        added = load(conn, parse(text.lstrip("﻿")))
        total = conn.execute("SELECT count(*) FROM church").fetchone()[0]
    except ChurchListError as error:
        print(f"Nothing loaded: {error}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print(f"Added {len(added)} churches. {total} in the list now.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
