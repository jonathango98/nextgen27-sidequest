"""Conference sessions: the admin's list, End session, and auto-pause (DATA-014, GAME-021,
GAME-026, GAME-107, OPS-002).

Start times are typed in venue time (GAME-105) and saved in UTC (DATA-004). Only admins see them
(DATA-014). Every change writes an audit row in the same transaction (ARCH-040, ARCH-050).
"""

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.auth.signup import PUBLIC_ID_CHARS, PUBLIC_ID_LENGTH
from app.services import audit, game_state

# Not a game number: the longest title the form takes, so a pasted paragraph can't fill the list.
TITLE_MAX_CHARS = 120
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# What <input type="datetime-local"> sends and shows.
LOCAL_INPUT_FORMAT = "%Y-%m-%dT%H:%M"
# Fake (SAFE-031). The hand test adds Example Session 1 itself (ENG-113).
PREVIEW_SESSION = "Example Session 2"
# An ended session, so players can write takeaways on the preview right away (journal.share-review).
PREVIEW_ENDED_SESSION = "Example Ended Session"

_COLUMNS = "id, public_id, title, starts_at, checkin_open_minutes, ended_at"


class SessionError(ValueError):
    """The form was filled in wrong. The message is shown to the admin (API-005)."""


class SessionNotFound(LookupError):
    pass


@dataclass(frozen=True)
class Details:
    title: str
    starts_at: str | None  # UTC
    checkin_open_minutes: int | None


@dataclass(frozen=True)
class Session:
    id: int
    public_id: str
    title: str
    starts_at: str | None
    checkin_open_minutes: int | None
    ended_at: str | None


@dataclass(frozen=True)
class Ended:
    title: str
    ended: bool  # False when it had already ended, so nothing changed
    resumed: bool  # the game went from paused to on


def _session(row: sqlite3.Row) -> Session:
    return Session(**dict(row))


def now_utc() -> str:
    # UTC_FORMAT sorts as text, so start times compare with plain <= in SQL.
    return datetime.now(UTC).strftime(UTC_FORMAT)


def _auto_pause_done(starts_at: str | None, now: str) -> str | None:
    # GAME-107: a start time already past when saved counts as done, so saving it never pauses.
    return now if starts_at is not None and starts_at <= now else None


def to_utc(local: str, timezone: str) -> str:
    venue = datetime.strptime(local, LOCAL_INPUT_FORMAT).replace(
        tzinfo=ZoneInfo(timezone)
    )
    return venue.astimezone(UTC).strftime(UTC_FORMAT)


def to_local(utc: str, timezone: str) -> datetime:
    return (
        datetime.strptime(utc, UTC_FORMAT)
        .replace(tzinfo=UTC)
        .astimezone(ZoneInfo(timezone))
    )


def read_details(form: dict[str, str], timezone: str) -> Details:
    """Check the add or edit form. Raises SessionError with a message for the admin."""
    title = " ".join(form.get("title", "").split())
    if not title:
        raise SessionError("Please give the session a title.")
    if len(title) > TITLE_MAX_CHARS:
        raise SessionError(f"Please keep the title to {TITLE_MAX_CHARS} characters.")
    start = form.get("starts_at", "").strip()
    minutes = form.get("checkin_open_minutes", "").strip()
    if not start:
        if minutes:
            raise SessionError("Check-in minutes need a start time too.")
        return Details(title, None, None)
    try:
        starts_at = to_utc(start, timezone)
    except ValueError:
        raise SessionError("Please pick a start date and time.") from None
    # GAME-021: with a start time, the admin says how early check-in opens (DATA-014).
    if not minutes:
        raise SessionError(
            "Please say how many minutes before the start check-in opens."
        )
    if not minutes.isdecimal() or int(minutes) < 1:
        raise SessionError("Check-in minutes must be a whole number above 0.")
    return Details(title, starts_at, int(minutes))


def list_all(conn: sqlite3.Connection) -> list[Session]:
    # Sessions with a start time in program order, then the ones without.
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM session ORDER BY starts_at IS NULL, starts_at, id"
    )
    return [_session(row) for row in rows]


def _find(conn: sqlite3.Connection, public_id: str) -> Session:
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM session WHERE public_id = ?", (public_id,)
    ).fetchone()
    if row is None:
        raise SessionNotFound(public_id)
    return _session(row)


def _insert(conn: sqlite3.Connection, d: Details, now: str) -> int:
    while True:
        public_id = "".join(
            secrets.choice(PUBLIC_ID_CHARS) for _ in range(PUBLIC_ID_LENGTH)
        )
        try:
            return conn.execute(
                "INSERT INTO session (public_id, title, starts_at, checkin_open_minutes,"
                " auto_pause_done_at) VALUES (?, ?, ?, ?, ?)",
                (
                    public_id,
                    d.title,
                    d.starts_at,
                    d.checkin_open_minutes,
                    _auto_pause_done(d.starts_at, now),
                ),
            ).lastrowid
        except sqlite3.IntegrityError as error:
            if "session.public_id" in str(error):
                continue  # DATA-003: astronomically rare, pick another
            raise


def _audit(conn: sqlite3.Connection, admin_id: int, action: str, session_id: int):
    audit.record(
        conn,
        actor_type="admin",
        actor_id=admin_id,
        action=action,
        target_type="session",
        target_id=session_id,
    )


def add(
    conn: sqlite3.Connection, d: Details, admin_id: int, now: str | None = None
) -> None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        _audit(conn, admin_id, "session_add", _insert(conn, d, now or now_utc()))
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def edit(
    conn: sqlite3.Connection,
    public_id: str,
    d: Details,
    admin_id: int,
    now: str | None = None,
) -> bool:
    """Save new details. Returns whether anything changed. Saving the same details writes nothing.

    A new start time resets auto-pause (GAME-107): moved later, the game pauses at the new time.
    Moved into the past, it counts as done, so saving never pauses the game.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        old = _find(conn, public_id)
        changed = (old.title, old.starts_at, old.checkin_open_minutes) != (
            d.title,
            d.starts_at,
            d.checkin_open_minutes,
        )
        if changed:
            conn.execute(
                "UPDATE session SET title = ?, starts_at = ?, checkin_open_minutes = ?"
                " WHERE id = ?",
                (d.title, d.starts_at, d.checkin_open_minutes, old.id),
            )
            if d.starts_at != old.starts_at:
                conn.execute(
                    "UPDATE session SET auto_pause_done_at = ? WHERE id = ?",
                    (_auto_pause_done(d.starts_at, now or now_utc()), old.id),
                )
            _audit(conn, admin_id, "session_edit", old.id)
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return changed


def end(conn: sqlite3.Connection, public_id: str, admin_id: int) -> Ended:
    """End session (GAME-026, OPS-002), all in one step or not at all (ARCH-040).

    Opens takeaways (GAME-036), closes check-in if it is still open (GAME-024), and turns a
    paused game on. An off game stays off, like GAME-107 never wakes it. A session that already
    ended changes nothing, so a second press or a stale tab can't resume the game again.
    """
    # ARCH-013: IMMEDIATE takes the write lock first, so two admins pressing at once queue.
    conn.execute("BEGIN IMMEDIATE")
    try:
        session = _find(conn, public_id)
        if session.ended_at is not None:
            conn.execute("COMMIT")
            return Ended(session.title, ended=False, resumed=False)
        conn.execute(
            "UPDATE session SET ended_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),"
            " checkin_closed_at = coalesce(checkin_closed_at,"
            " strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) WHERE id = ?",
            (session.id,),
        )
        _audit(conn, admin_id, "session_end", session.id)
        resumed = game_state.current_state(conn) == "paused"
        if resumed:
            game_state.change_in_transaction(conn, "on", admin_id)
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return Ended(session.title, ended=True, resumed=resumed)


def apply_auto_pause(conn: sqlite3.Connection, now: str, enabled: bool) -> bool:
    """Pause the game for any session whose start time has passed (GAME-107, DEC-051).

    Runs before each request (app/main.py), so the very next request sees the pause
    (ARCH-042). It is only a backup: admins still pause by hand (OPS-001). It acts only while
    the game is on, and never resumes it. Each start time is marked done once it passes,
    whatever the state was, so an admin who resumes by hand is never paused again.
    Returns whether it paused the game.
    """
    if not enabled:  # game.auto_pause_schedule
        return False
    due = "starts_at <= ? AND auto_pause_done_at IS NULL AND ended_at IS NULL"
    # A plain read first, so the write lock is taken only once for each start time.
    if not conn.execute(
        f"SELECT 1 FROM session WHERE {due} LIMIT 1", (now,)
    ).fetchone():
        return False
    # ARCH-013: two requests at the same moment queue here, and the second finds nothing due.
    conn.execute("BEGIN IMMEDIATE")
    try:
        started = [
            row["id"]
            for row in conn.execute(
                f"SELECT id FROM session WHERE {due} ORDER BY starts_at, id", (now,)
            )
        ]
        conn.execute(
            f"UPDATE session SET auto_pause_done_at = ? WHERE {due}", (now, now)
        )
        paused = bool(started) and game_state.current_state(conn) == "on"
        if paused:
            game_state.set_state(conn, "paused")
            audit.record(
                conn,
                actor_type="system",
                actor_id=None,
                action="auto_pause",
                target_type="session",
                target_id=started[-1],  # the one that started last
            )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return paused


def seed_preview(conn: sqlite3.Connection) -> list[str]:
    """A PR preview starts with no sessions. Adds two fake sessions, once (ENG-113).

    One is not ended yet, for End session. The other has ended, so takeaways are open.
    """
    added = []
    for title, ended in ((PREVIEW_SESSION, False), (PREVIEW_ENDED_SESSION, True)):
        if conn.execute("SELECT 1 FROM session WHERE title = ?", (title,)).fetchone():
            continue
        session_id = _insert(conn, Details(title, None, None), now_utc())
        if ended:
            conn.execute(
                "UPDATE session SET ended_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"
                " WHERE id = ?",
                (session_id,),
            )
        added.append(title)
    return added
