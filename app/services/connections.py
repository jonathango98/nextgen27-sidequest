"""Meeting someone: one player scans another's My Code (GAME-013, GAME-014, GAME-017).

The server checks every rule before it saves anything (ARCH-026). A scan gives no points.
They come when each player saves the answer they typed for the other (GAME-016).
"""

import random
import sqlite3
from dataclasses import dataclass

from app.services import churches, players, points
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

# Not a game number: the same limit as the check in migration 0009, so an answer can't
# become a message (SAFE-005).
ANSWER_MAX_CHARS = 200
EMPTY_ANSWER = (400, "BAD_INPUT", "Type their answer first.")
LONG_ANSWER = (400, "BAD_INPUT", f"Keep it to {ANSWER_MAX_CHARS} characters.")
ALREADY_ANSWERED = (409, "ALREADY_DONE", "You already saved this answer.")

# ENG-113: the hand test scans between two phones, so a preview also gets Test Player 2,
# from another church. No pair is saved, so the first scan on the preview is a new one.
PREVIEW_FRIEND = ("Test", "Player 2")


class AnswerRefused(ScanRefused):
    """A refused answer, with a status, error code, and message like a refused scan (API-005)."""


@dataclass(frozen=True)
class Connection:
    id: int
    question: str
    other_first_name: str  # SAFE-004: other players see first name and church only
    other_church: str
    my_answer: str | None = None  # SAFE-006: only ever the answer this player typed


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
        "SELECT c.id, c.question_category, p.first_name, ch.name AS church,"
        " a.answer_text"
        " FROM connection AS c"
        " JOIN player AS p ON p.id = CASE WHEN c.player_low_id = :me"
        "   THEN c.player_high_id ELSE c.player_low_id END"
        " JOIN church AS ch ON ch.id = p.church_id"
        " LEFT JOIN icebreaker_answer AS a"
        "   ON a.connection_id = c.id AND a.typed_by_player_id = :me"
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
        my_answer=row["answer_text"],
    )


def _insert_answer(conn, connection_id: int, about_id: int, me: int, text: str) -> int:
    try:
        return conn.execute(
            "INSERT INTO icebreaker_answer"
            " (connection_id, about_player_id, typed_by_player_id, answer_text)"
            " VALUES (?, ?, ?, ?)",
            (connection_id, about_id, me, text),
        ).lastrowid
    except sqlite3.IntegrityError as error:
        # DATA-032: the unique row is the duplicate check, so two taps on Save pay once.
        if str(error).startswith("UNIQUE constraint failed: icebreaker_answer."):
            raise AnswerRefused(*ALREADY_ANSWERED) from error
        raise


def _awards(conn, pair, me: int, points_cfg: dict) -> list[tuple[str, int]]:
    """The points this answer earns its typer (GAME-010, GAME-011, GAME-012)."""
    # GAME-018: same church means the churches the two picked at sign-up, saved at the scan.
    if pair["is_same_church"]:
        return [("connect_same_church", points_cfg["connect_same_church"])]
    awards = [("connect_other_church", points_cfg["connect_other_church"])]
    # GAME-011, DATA-021: the bonus row is the "first time" check, judged for this player only.
    first_time = conn.execute(
        "INSERT OR IGNORE INTO church_met (player_id, church_id, connection_id)"
        " VALUES (?, ?, ?)",
        (me, pair["other_church_id"], pair["id"]),
    ).rowcount
    if first_time:
        awards.append(
            ("connect_new_church_bonus", points_cfg["connect_new_church_bonus"])
        )
    return awards


def save_answer(
    conn: sqlite3.Connection,
    *,
    connection_id: int,
    player_id: int,
    text: str,
    config: dict,
) -> int:
    """Save the answer this player typed for the other person, and give their points.

    Returns the points earned (GAME-016). Raises AnswerRefused, or GameNotOn while paused
    or off (GAME-102, GAME-108), and then saves nothing.
    """
    text = text.strip()
    if not text:
        raise AnswerRefused(*EMPTY_ANSWER)
    if len(text) > ANSWER_MAX_CHARS:
        raise AnswerRefused(*LONG_ANSWER)

    # ARCH-013: IMMEDIATE takes the write lock first, so two taps on Save queue.
    conn.execute("BEGIN IMMEDIATE")
    try:
        # ARCH-042: read the state inside the transaction that saves the answer.
        require_game_on(conn)
        pair = conn.execute(
            "SELECT c.id, c.is_same_church, other.id AS other_id,"
            " other.church_id AS other_church_id"
            " FROM connection AS c"
            " JOIN player AS other ON other.id = CASE WHEN c.player_low_id = :me"
            "   THEN c.player_high_id ELSE c.player_low_id END"
            " WHERE c.id = :id AND :me IN (c.player_low_id, c.player_high_id)",
            {"id": connection_id, "me": player_id},
        ).fetchone()
        if pair is None:
            raise AnswerRefused(
                *NOT_FOUND
            )  # SAFE-006: outside the pair, same as missing
        # GAME-015: each person types the other person's answer.
        answer_id = _insert_answer(conn, pair["id"], pair["other_id"], player_id, text)
        earned = 0
        for reason, amount in _awards(conn, pair, player_id, config["points"]):
            # AI-041: every award goes through the one points service, in this transaction.
            points.award(
                conn,
                player_id=player_id,
                reason_code=reason,
                amount=amount,
                source_type="icebreaker_answer",
                source_id=answer_id,
            )
            earned += amount
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return earned


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
