"""What an usher may see about a player when finding them (GAME-112, GAME-113)."""

import sqlite3
from dataclasses import dataclass

from app.auth.signup import NAME_MAX_CHARS

# Not game numbers: limits that keep one search small. A full name is two names and a space.
QUERY_MAX_CHARS = 2 * NAME_MAX_CHARS + 1
RESULTS_MAX = 20

# SAFE-004, SAFE-028: only these columns are read, so a full last name, the under-18 answer,
# and the PIN hash cannot reach an usher's page by accident.
_SELECT = (
    "SELECT p.public_id, p.first_name, substr(p.last_name, 1, 1) AS last_initial,"
    " c.name AS church FROM player p JOIN church c ON c.id = p.church_id"
)


@dataclass(frozen=True)
class PlayerForUsher:
    public_id: str
    first_name: str
    last_initial: str
    church: str


def _from_row(row: sqlite3.Row) -> PlayerForUsher:
    return PlayerForUsher(
        public_id=row["public_id"],
        first_name=row["first_name"],
        last_initial=row["last_initial"].upper(),
        church=row["church"],
    )


def clean_query(query: str) -> str:
    return " ".join(query.split())[:QUERY_MAX_CHARS]


def search(conn: sqlite3.Connection, query: str) -> tuple[list[PlayerForUsher], bool]:
    """Players whose first, last, or full name starts with the query, and whether there are more."""
    query = clean_query(query)
    if not query:
        return [], False  # never a way to list every player
    # A typed % or _ is a letter to look for, not a wildcard.
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"{escaped}%"
    rows = conn.execute(
        f"{_SELECT} WHERE p.first_name LIKE ? ESCAPE '\\'"
        " OR p.last_name LIKE ? ESCAPE '\\'"
        " OR p.first_name || ' ' || p.last_name LIKE ? ESCAPE '\\'"
        " ORDER BY p.first_name COLLATE NOCASE, p.last_name COLLATE NOCASE, c.name"
        " LIMIT ?",
        (pattern, pattern, pattern, RESULTS_MAX + 1),
    ).fetchall()
    return [_from_row(row) for row in rows[:RESULTS_MAX]], len(rows) > RESULTS_MAX


def find(conn: sqlite3.Connection, public_id: str) -> PlayerForUsher | None:
    row = conn.execute(f"{_SELECT} WHERE p.public_id = ?", (public_id,)).fetchone()
    return None if row is None else _from_row(row)
