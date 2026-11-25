"""The audit log: one write-once row for every important action (ARCH-050, DATA-015).

There is no update or delete here on purpose. Only the retention cleanup removes rows (SAFE-014).
"""

import re
import sqlite3
from dataclasses import dataclass

ACTOR_TYPES = frozenset({"system", "player", "usher", "admin", "screen"})
CODE = re.compile(r"^[a-z0-9_]{1,64}$")


class AuditError(ValueError):
    pass


def record(
    conn: sqlite3.Connection,
    *,
    actor_type: str,
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    reason: str | None = None,
) -> int:
    """Write one audit row and return its id.

    Runs inside the caller's transaction, so an action and its audit row save together (ARCH-040).
    Pass internal IDs only, never names or PINs (ARCH-051). `reason` is staff-written, never text
    a player typed.
    """
    if actor_type not in ACTOR_TYPES:
        raise AuditError(f"Unknown actor type: {actor_type!r}")
    if (actor_type == "system") != (actor_id is None):
        raise AuditError("Only the system acts without an actor id")
    if not CODE.match(action):
        raise AuditError("Action must be a short code like pin_reset")
    if (target_type is None) != (target_id is None):
        raise AuditError("Give both target_type and target_id, or neither")
    if target_type is not None and not CODE.match(target_type):
        raise AuditError("Target type must be a short code like player")
    for value in (actor_id, target_id):
        if value is not None and type(value) is not int:
            raise AuditError("IDs must be internal integer IDs")
    if reason is not None:
        reason = reason.strip() or None
    return conn.execute(
        "INSERT INTO audit_log"
        " (actor_type, actor_id, action, target_type, target_id, reason)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (actor_type, actor_id, action, target_type, target_id, reason),
    ).lastrowid


# Not a game number: how many rows one page of the admin log shows (ARCH-050).
PAGE_ROWS = 100
_ACTOR_LABELS = {"system": "System", "screen": "Main screen"}

# GAME-112 style names: first name, last initial, and church. Only IDs are stored (ARCH-051),
# so names are looked up when the page loads.
_RECENT = (
    "SELECT a.id, a.actor_type, a.actor_id, a.action, a.target_type, a.target_id, a.reason,"
    " a.created_at, s.username,"
    " ap.first_name AS actor_first, substr(ap.last_name, 1, 1) AS actor_initial,"
    " ac.name AS actor_church,"
    " tp.first_name AS target_first, substr(tp.last_name, 1, 1) AS target_initial,"
    " tc.name AS target_church"
    " FROM audit_log a"
    " LEFT JOIN staff_account s ON a.actor_type IN ('usher', 'admin') AND s.id = a.actor_id"
    " LEFT JOIN player ap ON a.actor_type = 'player' AND ap.id = a.actor_id"
    " LEFT JOIN church ac ON ac.id = ap.church_id"
    " LEFT JOIN player tp ON a.target_type = 'player' AND tp.id = a.target_id"
    " LEFT JOIN church tc ON tc.id = tp.church_id"
    " WHERE ? IS NULL OR a.id < ?"
    " ORDER BY a.id DESC LIMIT ?"
)


@dataclass(frozen=True)
class Entry:
    id: int
    created_at: str
    who: str
    action: str
    target: str
    reason: str | None


def person(first: str | None, initial: str | None, church: str | None) -> str | None:
    return f"{first} {initial.upper()}., {church}" if first else None


def _who(row: sqlite3.Row) -> str:
    kind, actor_id = row["actor_type"], row["actor_id"]
    if kind in _ACTOR_LABELS:
        return _ACTOR_LABELS[kind]
    if kind == "player":
        name = person(row["actor_first"], row["actor_initial"], row["actor_church"])
        return name or f"player {actor_id}"
    return f"{row['username'] or actor_id} ({kind})"


def _target(row: sqlite3.Row) -> str:
    if row["target_type"] is None:
        return ""
    if row["target_type"] == "player":
        name = person(row["target_first"], row["target_initial"], row["target_church"])
        if name:
            return name
    return f"{row['target_type'].replace('_', ' ')} {row['target_id']}"


def recent(
    conn: sqlite3.Connection, before: int | None = None
) -> tuple[list[Entry], int | None]:
    """One page of the log, newest first, and the id to pass as `before` for older rows."""
    rows = conn.execute(_RECENT, (before, before, PAGE_ROWS + 1)).fetchall()
    entries = [
        Entry(
            id=r["id"],
            created_at=r["created_at"],
            who=_who(r),
            action=r["action"].replace("_", " "),
            target=_target(r),
            reason=r["reason"],
        )
        for r in rows[:PAGE_ROWS]
    ]
    older = entries[-1].id if len(rows) > PAGE_ROWS else None
    return entries, older
