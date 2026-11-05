"""What the main screen shows (UI-040, UI-044, API-031, DEC-069).

While the game is on or paused, the main screen takes turns through VIEWS. While it is off, it
shows the off view an admin picked: the offline message or the recap.
"""

import sqlite3

from app.services import audit
from app.services.game_state import current_state

# UI-040: the views in the order they take turns. The first one follows the last.
VIEWS = ("players", "churches", "takeaways")
# UI-044: what the main screen can show while the game is off.
OFF_VIEWS = ("offline", "recap")
# ARCH-050: the audit action for each off view an admin picks.
AUDIT_ACTIONS = {"offline": "screen_off_offline", "recap": "screen_off_recap"}


class UnknownOffView(ValueError):
    pass


def next_view(view: str) -> str:
    return VIEWS[(VIEWS.index(view) + 1) % len(VIEWS)]


def off_view(conn: sqlite3.Connection) -> str:
    # ARCH-042: read on every call, so a switch shows at the next turn.
    return conn.execute(
        "SELECT screen_off_view FROM game_state WHERE id = 1"
    ).fetchone()["screen_off_view"]


def showing(conn: sqlite3.Connection, view: str) -> str:
    """The view to show in place of `view`: itself, or the off view while the game is off.

    Pause does not stop the main screen (DEC-069). Only off does (UI-040).
    """
    return off_view(conn) if current_state(conn) == "off" else view


def change_off_view(conn: sqlite3.Connection, view: str, admin_id: int) -> bool:
    """An admin picks the off view (UI-044). Returns whether it changed.

    The choice and its audit row save together, or neither does (ARCH-040, ARCH-050).
    Picking the view already shown writes nothing.
    """
    if view not in OFF_VIEWS:
        raise UnknownOffView(view)
    # ARCH-013: IMMEDIATE takes the write lock first, so two admins pressing at once queue.
    conn.execute("BEGIN IMMEDIATE")
    try:
        changed = off_view(conn) != view
        if changed:
            conn.execute(
                "UPDATE game_state SET screen_off_view = ?, updated_by = ?,"
                " updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = 1",
                (view, admin_id),
            )
            audit.record(
                conn,
                actor_type="admin",
                actor_id=admin_id,
                action=AUDIT_ACTIONS[view],
                target_type="game_state",
                target_id=1,
            )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return changed
