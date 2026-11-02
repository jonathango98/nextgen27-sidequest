"""The game's one switch: on, paused, or off (GAME-100, DATA-013)."""

import sqlite3

from app.services import audit

# API-020: the error code for each state that refuses earning actions.
REFUSED = {"paused": "PAUSED", "off": "GAME_OFF"}
# API-020: friendly message for each 423 code, from 06-api-and-screens.md section 3.
GAME_NOT_ON_MESSAGES = {
    "PAUSED": "The game is paused during the session.",
    "GAME_OFF": "The game is closed right now.",
}
# UI-033: the short note on every player page while the game is not on. Never scolds.
BANNERS = {"paused": "Game paused", "off": GAME_NOT_ON_MESSAGES["GAME_OFF"]}
# ARCH-050: the audit action for each state an admin picks. `pause` is the example in DATA-015.
AUDIT_ACTIONS = {"on": "game_on", "paused": "pause", "off": "game_off"}


class GameNotOn(Exception):
    def __init__(self, error_code: str):
        super().__init__(error_code)
        self.error_code = error_code


class UnknownState(ValueError):
    pass


def current_state(conn: sqlite3.Connection) -> str:
    # ARCH-042: read on every call, never cached, so a change applies to the next request.
    return conn.execute("SELECT state FROM game_state WHERE id = 1").fetchone()["state"]


def set_state(
    conn: sqlite3.Connection, state: str, updated_by: int | None = None
) -> None:
    # The check constraint refuses any state not in game.states (DATA-013).
    # An admin's press goes through change() instead, which also writes the audit row (ARCH-050).
    conn.execute(
        "UPDATE game_state SET state = ?, updated_by = ?,"
        " updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = 1",
        (state, updated_by),
    )


def change(
    conn: sqlite3.Connection, state: str, admin_id: int, states: list[str]
) -> bool:
    """An admin presses Start, Pause, or Off (GAME-101, GAME-110). Returns whether it changed.

    The new state and its audit row save together, or neither does (ARCH-040, ARCH-050).
    Pressing the state the game is already in writes nothing.
    """
    if state not in states:
        raise UnknownState(state)
    # ARCH-013: IMMEDIATE takes the write lock first, so two admins pressing at once queue.
    conn.execute("BEGIN IMMEDIATE")
    try:
        changed = current_state(conn) != state
        if changed:
            set_state(conn, state, updated_by=admin_id)
            audit.record(
                conn,
                actor_type="admin",
                actor_id=admin_id,
                action=AUDIT_ACTIONS[state],
                target_type="game_state",
                target_id=1,
            )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return changed


def require_game_on(conn: sqlite3.Connection) -> None:
    """Raise GameNotOn unless the game is on (ARCH-041, GAME-102, GAME-108).

    Call it inside the same transaction that saves the earning, so a request
    that was already saving when the state changed finishes normally (ARCH-042).
    """
    error_code = REFUSED.get(current_state(conn))
    if error_code:
        raise GameNotOn(error_code)
