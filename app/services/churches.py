"""Loads the church list from a CSV kept outside the repo (SAFE-002, DEC-011).

Usage: python -m app.services.churches <file.csv>   (or "-" to read from stdin)

The CSV has one column, "name". Region is not loaded while DATA-010 is OPEN.
The real list is real event data, so it never goes in the repo (SAFE-030, ARCH-007).
"""

import csv
import io
import sqlite3
import sys

from app.db import connect, db_path_from_env, migrate

HEADER = ["name"]


class ChurchListError(Exception):
    pass


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
