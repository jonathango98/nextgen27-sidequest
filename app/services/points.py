"""The one points service: every point award goes through award() (ARCH-040, AI-041).

The server is the only authority for points (GAME-002, AI-040). Callers pass the amount
they read from game-config.yaml (AI-013). This service never trusts a number from the phone.
"""

import sqlite3

from app.services import audit
from app.services.game_state import current_state, require_game_on


class AlreadyAwarded(Exception):
    """This record already paid this player (DATA-027). Routes map it to their own 409 code."""


def _save_award(conn, player_id, reason_code, amount, source_type, source_id) -> int:
    try:
        ledger_id = conn.execute(
            "INSERT INTO point_ledger"
            " (player_id, amount, reason_code, source_type, source_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (player_id, amount, reason_code, source_type, source_id),
        ).lastrowid
    except sqlite3.IntegrityError as error:
        # DATA-027: the unique index is the duplicate check, so a race can't slip past it.
        if str(error).startswith("UNIQUE constraint failed: point_ledger."):
            raise AlreadyAwarded from error
        raise
    audit.record(
        conn,
        actor_type="system",
        actor_id=None,
        action="points_award",
        target_type="point_ledger",
        target_id=ledger_id,
    )
    return ledger_id


def _award(conn, player_id, reason_code, amount, source_type, source_id) -> int:
    # ARCH-041, ARCH-042: read the state inside the transaction that saves the award.
    require_game_on(conn)
    return _save_award(conn, player_id, reason_code, amount, source_type, source_id)


def _in_transaction(conn, write):
    # Inside the caller's transaction, join it. Otherwise open and commit our own.
    if conn.in_transaction:
        return write()
    # ARCH-013: IMMEDIATE takes the write lock first, so two awards queue instead of racing.
    conn.execute("BEGIN IMMEDIATE")
    try:
        result = write()
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return result


def award(
    conn: sqlite3.Connection,
    *,
    player_id: int,
    reason_code: str,
    amount: int,
    source_type: str,
    source_id: int,
) -> int:
    """Give a system award once and return the ledger row id (ARCH-040).

    Checks the game state, then duplicates, then writes the ledger row and its audit row,
    all in one transaction. Raises GameNotOn (423) or AlreadyAwarded, and then saves nothing.
    Inside the caller's transaction it joins it, so a quest saves its record and its points
    together. Otherwise it opens and commits its own.
    """
    if amount <= 0:
        raise ValueError("System awards are positive (GAME-004)")
    return _in_transaction(
        conn,
        lambda: _award(conn, player_id, reason_code, amount, source_type, source_id),
    )


def award_join(
    conn: sqlite3.Connection, *, player_id: int, amount: int, while_paused: bool
) -> int | None:
    """Give a player their join points once (GAME-040) and return the ledger row id.

    The only earning allowed while paused (GAME-044, GAME-102, API-020), so its reason and
    source are fixed here and no other quest can use it to get around a pause. If
    join.points_while_paused is turned off, it pays nothing during a pause and returns None,
    because sign-up stays open (GAME-102). Raises GameNotOn while the game is off (GAME-108).
    """
    if amount <= 0:
        raise ValueError("System awards are positive (GAME-004)")

    def write():
        state = current_state(conn)
        if state == "paused" and not while_paused:
            return None
        if state != "paused":
            require_game_on(conn)
        return _save_award(conn, player_id, "join", amount, "player", player_id)

    return _in_transaction(conn, write)


def score(conn: sqlite3.Connection, player_id: int) -> int:
    # DATA-030: the score is the sum of the ledger, never a stored number that could drift.
    return conn.execute(
        "SELECT coalesce(sum(amount), 0) FROM point_ledger WHERE player_id = ?",
        (player_id,),
    ).fetchone()[0]
