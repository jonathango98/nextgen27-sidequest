"""Meeting someone: one player scans another's My Code (GAME-013, GAME-014, GAME-017).

The server checks every rule before it saves anything (ARCH-026). Points are not given here.
They come when each player saves their answer (GAME-016, connections.answers).
"""

import random
import sqlite3
from dataclasses import dataclass

from app.services import churches, players
from app.services.game_state import require_game_on
from app.services.players import NOT_FOUND, ScanRefused

# GAME-019: the question for each key in icebreaker.categories (02-game-rules.md section 3).
# SAFE-043: none of them ask for contact details, social handles, or where someone stays.
QUESTIONS = {
    "verse": "Favorite Bible verse?",
    "food": "Favorite food?",
    "game": "Best youth group game you've played?",
    "song": "A worship song you can't stop singing?",
    "place": "Dream place to visit?",
    "hobby": "What do you do for fun?",
}


# API-005: the refusals this adds to the ones in players (06 section 3).
# GAME-014: 06 has no code of its own for scanning yourself, so it is a wrong input (BAD_INPUT).
OWN_CODE = (400, "BAD_INPUT", "That's your own code! Scan a friend's.")
ALREADY_CONNECTED = (409, "ALREADY_CONNECTED", "You two are already connected!")

# ENG-113: the hand test scans between two phones, so a preview also gets Test Player 2,
# from another church. No pair is saved, so the first scan on the preview is a new one.
PREVIEW_FRIEND = ("Test", "Player 2")


@dataclass(frozen=True)
class Connection:
    id: int
    question: str
    other_first_name: str  # SAFE-004: other players see first name and church only
    other_church: str


def _player_id(conn: sqlite3.Connection, public_id: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM player WHERE public_id = ?", (public_id,)
    ).fetchone()
    return row["id"] if row else None


def _save(conn, scanner_id: int, scanned_id: int, category: str) -> int:
    low, high = sorted((scanner_id, scanned_id))
    try:
        return conn.execute(
            "INSERT INTO connection"
            " (player_low_id, player_high_id, scanner_id, question_category, is_same_church)"
            " SELECT ?, ?, ?, ?, low.church_id = high.church_id"
            " FROM player AS low, player AS high WHERE low.id = ? AND high.id = ?",
            (low, high, scanner_id, category, low, high),
        ).lastrowid
    except sqlite3.IntegrityError as error:
        # GAME-013: the unique pair is the duplicate check, so two phones scanning
        # each other at the same moment still save one row.
        if str(error).startswith("UNIQUE constraint failed: connection."):
            raise ScanRefused(*ALREADY_CONNECTED) from error
        raise


def scan(
    conn: sqlite3.Connection,
    *,
    scanner_public_id: str,
    payload: str,
    now: float,
    config: dict,
) -> Connection:
    """Save that the scanner met the player whose code they scanned, and pick their question.

    Raises ScanRefused, or GameNotOn while paused or off (GAME-102, GAME-108), and then
    saves nothing.
    """
    # ARCH-025, ARCH-022, ARCH-026: a player code, checked by the server. Shared with the usher console.
    scanned_public_id = players.public_id_from_scan(payload.strip(), now, config["qr"])
    if scanned_public_id == scanner_public_id:
        raise ScanRefused(*OWN_CODE)  # GAME-014
    # GAME-019: one question per pair, saved with the pair so both phones show the same one.
    category = random.choice(config["icebreaker"]["categories"])

    # ARCH-013: IMMEDIATE takes the write lock first, so two scans queue instead of racing.
    conn.execute("BEGIN IMMEDIATE")
    try:
        # ARCH-042: read the state inside the transaction that saves the scan.
        require_game_on(conn)
        scanner_id = _player_id(conn, scanner_public_id)
        scanned_id = _player_id(conn, scanned_public_id)
        if scanner_id is None or scanned_id is None:
            raise ScanRefused(*NOT_FOUND)
        connection_id = _save(conn, scanner_id, scanned_id, category)
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return for_player(conn, connection_id, scanner_id)


def for_player(
    conn: sqlite3.Connection, connection_id: int, player_id: int
) -> Connection | None:
    """The connection as one of its two players sees it, or None for anyone else (SAFE-006)."""
    row = conn.execute(
        "SELECT c.id, c.question_category, p.first_name, ch.name AS church"
        " FROM connection AS c"
        " JOIN player AS p ON p.id = CASE WHEN c.player_low_id = :me"
        "   THEN c.player_high_id ELSE c.player_low_id END"
        " JOIN church AS ch ON ch.id = p.church_id"
        " WHERE c.id = :id AND :me IN (c.player_low_id, c.player_high_id)",
        {"id": connection_id, "me": player_id},
    ).fetchone()
    if row is None:
        return None
    return Connection(
        id=row["id"],
        question=QUESTIONS[row["question_category"]],
        other_first_name=row["first_name"],
        other_church=row["church"],
    )


def latest_id(conn: sqlite3.Connection, player_id: int) -> int:
    """The newest connection this player is in, so My Code only notes newer ones (API-032)."""
    return conn.execute(
        "SELECT coalesce(max(id), 0) FROM connection"
        " WHERE ? IN (player_low_id, player_high_id)",
        (player_id,),
    ).fetchone()[0]


def incoming(conn: sqlite3.Connection, player_id: int, after: int) -> list[Connection]:
    """Connections newer than `after` where someone else scanned this player (API-032)."""
    rows = conn.execute(
        "SELECT id FROM connection"
        " WHERE id > ? AND ? IN (player_low_id, player_high_id) AND scanner_id <> ?"
        " ORDER BY id",
        (after, player_id, player_id),
    ).fetchall()
    return [for_player(conn, row["id"], player_id) for row in rows]


def seed_preview(conn: sqlite3.Connection, config: dict) -> list[str]:
    """Adds Test Player 2 to a PR preview, with the preview PIN (ENG-113, AI-047)."""
    return players.seed_preview_player(
        conn, config, PREVIEW_FRIEND, churches.EXAMPLE_CHURCHES[1]
    )
