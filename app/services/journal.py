"""Takeaways: a private note about what a player learned in a session (GAME-030 to GAME-036).

The server counts the words and gives the points (AI-040). Every note is private for now:
choosing who can read it comes with journal.share-review (GAME-031). Only the player who wrote
a note can list it (03-safety-privacy.md who-sees-what table).
"""

import sqlite3
from dataclasses import dataclass

from app.services import points
from app.services.game_state import require_game_on
from app.services.players import NOT_FOUND

# GAME-030: the reason on journal awards. The source is the session, so the ledger's unique
# award (DATA-027) pays once per session however many notes the player writes (DEC-072).
REASON = "journal_takeaway"
SOURCE_TYPE = "session"


class TakeawayRefused(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SessionChoice:
    public_id: str
    title: str
    paid: bool  # the player already got this session's points


@dataclass(frozen=True)
class Note:
    session_title: str
    text: str


@dataclass(frozen=True)
class Saved:
    points: int  # 0 when this session already paid (DEC-072)


def count_words(text: str) -> int:
    """GAME-034: split on spaces and line breaks. Punctuation alone, like "-", is not a word."""
    return sum(1 for token in text.split() if any(ch.isalnum() for ch in token))


def too_short(missing: int) -> TakeawayRefused:
    # API-005, 06 section 3: TOO_SHORT says how many more words are needed (GAME-030 example E6).
    word = "word" if missing == 1 else "words"
    return TakeawayRefused(400, "TOO_SHORT", f"Add {missing} more {word} to save this.")


def _open_sessions_sql(require_checkin: bool) -> str:
    # GAME-036: only sessions an admin has ended. GAME-035: a check-in only if config asks.
    sql = "SELECT s.id, s.public_id, s.title, s.ended_at FROM session AS s WHERE s.ended_at IS NOT NULL"
    if require_checkin:
        sql += " AND EXISTS (SELECT 1 FROM check_in AS c WHERE c.session_id = s.id AND c.player_id = :player)"
    return sql


def sessions_to_write(
    conn: sqlite3.Connection, player_id: int, *, require_checkin: bool
) -> list[SessionChoice]:
    """The sessions this player can write about, newest ended first."""
    rows = conn.execute(
        "SELECT o.public_id, o.title, EXISTS (SELECT 1 FROM point_ledger AS l"
        " WHERE l.player_id = :player AND l.reason_code = :reason"
        " AND l.source_type = :source AND l.source_id = o.id) AS paid"
        f" FROM ({_open_sessions_sql(require_checkin)}) AS o ORDER BY o.ended_at DESC, o.id DESC",
        {"player": player_id, "reason": REASON, "source": SOURCE_TYPE},
    ).fetchall()
    return [SessionChoice(r["public_id"], r["title"], bool(r["paid"])) for r in rows]


def submit(
    conn: sqlite3.Connection,
    *,
    player_id: int,
    session_public_id: str,
    text: str,
    min_words: int,
    amount: int,
    require_checkin: bool,
) -> Saved:
    """Save a private takeaway, and give the points if it is this session's first (GAME-030).

    Raises TakeawayRefused, or GameNotOn while paused or off (GAME-033, GAME-108), and then
    saves nothing.
    """
    text = text.strip()
    missing = min_words - count_words(text)
    if missing > 0:
        raise too_short(missing)

    # ARCH-013: IMMEDIATE takes the write lock first, so two taps queue instead of racing.
    conn.execute("BEGIN IMMEDIATE")
    try:
        # ARCH-042: read the state inside the transaction that saves the note.
        require_game_on(conn)
        session = conn.execute(
            f"SELECT o.id FROM ({_open_sessions_sql(require_checkin)}) AS o WHERE o.public_id = :id",
            {"player": player_id, "id": session_public_id},
        ).fetchone()
        if session is None:
            raise TakeawayRefused(*NOT_FOUND)  # GAME-036: not ended, or no such session
        conn.execute(
            "INSERT INTO takeaway (player_id, session_id, text) VALUES (?, ?, ?)",
            (player_id, session["id"], text),
        )
        try:
            points.award(
                conn,
                player_id=player_id,
                reason_code=REASON,
                amount=amount,
                source_type=SOURCE_TYPE,
                source_id=session["id"],
            )
            paid = amount
        except points.AlreadyAwarded:
            paid = 0  # DEC-072: a later note for the same session saves with no points
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return Saved(points=paid)


def list_own(conn: sqlite3.Connection, player_id: int) -> list[Note]:
    """Only this player's notes, newest session first, then newest note first (who-sees-what table)."""
    rows = conn.execute(
        "SELECT s.title, t.text FROM takeaway AS t JOIN session AS s ON s.id = t.session_id"
        " WHERE t.player_id = ? ORDER BY s.ended_at DESC, s.id DESC, t.id DESC",
        (player_id,),
    ).fetchall()
    return [Note(r["title"], r["text"]) for r in rows]
