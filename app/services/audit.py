"""The audit log: one write-once row for every important action (ARCH-050, DATA-015).

There is no update or delete here on purpose. Only the retention cleanup removes rows (SAFE-014).
"""

import re
import sqlite3

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
