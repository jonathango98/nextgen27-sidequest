"""What an usher may see about a player when finding them (GAME-112, GAME-113, DEC-065)."""

import os
import sqlite3
from dataclasses import dataclass

from app.auth import signup
from app.auth.signup import NAME_MAX_CHARS
from app.services import churches, qr

# Not game numbers: limits that keep one search small. A full name is two names and a space.
QUERY_MAX_CHARS = 2 * NAME_MAX_CHARS + 1
RESULTS_MAX = 20

# ENG-113: the fake player a PR preview starts with. An adult, so no minor's data is seeded (AI-047).
PREVIEW_PLAYER = ("Test", "Player 1")
PREVIEW_PIN_ENV = "SQ_PREVIEW_PLAYER_PIN"

# API-005: the status, code, and message for each refused scan, from 06 section 3.
NOT_A_CODE = (400, "NOT_A_CODE", "This isn't a Side Quest code.")
CODE_EXPIRED = (410, "CODE_EXPIRED", "That code expired. Ask them to show it again.")
NOT_FOUND = (404, "NOT_FOUND", "We couldn't find that.")

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


class ScanRefused(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message


def from_scan(
    conn: sqlite3.Connection, payload: str, now: float, qr_cfg: dict
) -> PlayerForUsher:
    """The player whose My Code this is. Only says who it is, and saves nothing (GAME-112)."""
    parts = payload.split(".")  # ARCH-020: SQ1.<kind>.<public_id>.<code>
    if (
        len(parts) != 4
        or parts[0] != qr_cfg["format_version"]
        or parts[1] != qr.PLAYER_KIND
        or not parts[2]
    ):
        raise ScanRefused(*NOT_A_CODE)  # ARCH-025
    # ARCH-026: the code in the payload proves nothing until the server has checked it.
    if not qr.verify(qr.PLAYER_KIND, parts[2], parts[3], now, qr_cfg):
        raise ScanRefused(*CODE_EXPIRED)  # ARCH-022
    player = find(conn, parts[2])
    if player is None:
        raise ScanRefused(*NOT_FOUND)
    return player


def seed_preview(conn: sqlite3.Connection, config: dict) -> list[str]:
    """A PR preview starts with no players. Adds Test Player 1 if its PIN variable is set (ENG-113)."""
    pin = os.environ.get(PREVIEW_PIN_ENV)
    church = conn.execute(
        "SELECT id FROM church WHERE name = ?", (churches.EXAMPLE_CHURCHES[0],)
    ).fetchone()
    if not pin or church is None:
        return []
    first, last = PREVIEW_PLAYER
    details = signup.Details(first, last, church["id"], False)
    try:
        signup.check_pin({"pin": pin, "pin_again": pin}, config["auth"]["pin_digits"])
        signup.create_player(conn, details, pin, config)
    except signup.SignupError:
        return []  # already there, a PIN of the wrong shape, or the game is off
    return [f"{first} {last}"]
