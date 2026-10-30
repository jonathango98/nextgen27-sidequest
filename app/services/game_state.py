"""The game's one switch: on, paused, or off (GAME-100, DATA-013)."""

import sqlite3

# API-020: the error code for each state that refuses earning actions.
REFUSED = {"paused": "PAUSED", "off": "GAME_OFF"}


class GameNotOn(Exception):
    def __init__(self, error_code: str):
        super().__init__(error_code)
        self.error_code = error_code


def current_state(conn: sqlite3.Connection) -> str:
    # ARCH-042: read on every call, never cached, so a change applies to the next request.
    return conn.execute("SELECT state FROM game_state WHERE id = 1").fetchone()["state"]


def set_state(
    conn: sqlite3.Connection, state: str, updated_by: int | None = None
) -> None:
    # The check constraint refuses any state not in game.states (DATA-013).
    # The admin buttons and their audit row come with game-state.controls (ARCH-050).
    conn.execute(
        "UPDATE game_state SET state = ?, updated_by = ?,"
        " updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = 1",
        (state, updated_by),
    )


def require_game_on(conn: sqlite3.Connection) -> None:
    """Raise GameNotOn unless the game is on (ARCH-041, GAME-102, GAME-108).

    Call it inside the same transaction that saves the earning, so a request
    that was already saving when the state changed finishes normally (ARCH-042).
    """
    error_code = REFUSED.get(current_state(conn))
    if error_code:
        raise GameNotOn(error_code)
