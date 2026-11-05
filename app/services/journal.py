"""Takeaways: a note about what a player learned in a session (GAME-030 to GAME-036).

The server counts the words and gives the points (AI-040). The player picks who can read each
note (GAME-031), and a shared note is read by an admin before anyone else sees it (SAFE-007).
Players see their own notes and approved shared ones, never anyone's private notes
(03-safety-privacy.md who-sees-what table).
"""

import sqlite3
from dataclasses import dataclass

from app.services import audit, points
from app.services.game_state import require_game_on
from app.services.players import NOT_FOUND

# GAME-030: the reason on journal awards. The source is the session, so the ledger's unique
# award (DATA-027) pays once per session however many notes the player writes (DEC-072).
REASON = "journal_takeaway"
SOURCE_TYPE = "session"

# GAME-031: who can read a note.
VISIBILITIES = ("private", "shared_named", "shared_anonymous")
SHARED = ("shared_named", "shared_anonymous")
# SAFE-040, SAFE-041, DEC-076: the outcome an admin picks, and the statuses it can start from.
# Approve also undoes a reject or a hide.
REVIEW_FROM = {
    "approve": ("pending", "rejected", "hidden"),
    "reject": ("pending",),
    "hide": ("approved",),
}
REVIEW_TO = {"approve": "approved", "reject": "rejected", "hide": "hidden"}
# DEC-076: a note an admin turned down can only stay private.
LOCKED = ("rejected", "hidden")
REVIEW_STATUSES = ("pending", "approved", "rejected", "hidden")

BAD_VISIBILITY = (400, "BAD_INPUT", "Please choose who can read this.")
STAY_PRIVATE = (400, "BAD_INPUT", "This note can only be kept private.")
ALREADY_REVIEWED = (
    409,
    "ALREADY_DONE",
    "Someone already reviewed this note. Refresh to see it.",
)


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
    public_id: str
    text: str
    visibility: str
    can_share: bool  # DEC-076: False once an admin rejected or hid it


@dataclass(frozen=True)
class SharedNote:
    """An approved shared note for players. Anonymous notes carry no name or church (SAFE-009)."""

    session_title: str
    text: str
    first_name: str | None
    church: str | None


@dataclass(frozen=True)
class ForReview:
    """A shared note for an admin, always with its author (SAFE-009, SAFE-042)."""

    public_id: str
    session_title: str
    text: str
    visibility: str
    review_status: str
    first_name: str
    last_name: str
    church: str


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


def _first_status(visibility: str, review_scope: str) -> str:
    if visibility not in VISIBILITIES:
        raise TakeawayRefused(*BAD_VISIBILITY)
    # SAFE-008: only the stricter option has a config value so far. Fail loudly on anything else.
    if review_scope != "all_shared":
        raise ValueError(f"Unknown journal.review_scope: {review_scope!r}")
    return "not_needed" if visibility == "private" else "pending"


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
    visibility: str,
    review_scope: str,
    min_words: int,
    amount: int,
    require_checkin: bool,
) -> Saved:
    """Save a takeaway, and give the points if it is this session's first (GAME-030).

    GAME-031: the points are the same whoever can read it. A shared note waits for review (SAFE-007).

    Raises TakeawayRefused, or GameNotOn while paused or off (GAME-033, GAME-108), and then
    saves nothing.
    """
    status = _first_status(visibility, review_scope)
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
            "INSERT INTO takeaway (player_id, session_id, text, visibility, review_status)"
            " VALUES (?, ?, ?, ?, ?)",
            (player_id, session["id"], text, visibility, status),
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
        "SELECT s.title, t.public_id, t.text, t.visibility, t.review_status"
        " FROM takeaway AS t JOIN session AS s ON s.id = t.session_id"
        " WHERE t.player_id = ? ORDER BY s.ended_at DESC, s.id DESC, t.id DESC",
        (player_id,),
    ).fetchall()
    return [
        Note(
            r["title"],
            r["public_id"],
            r["text"],
            r["visibility"],
            r["review_status"] not in LOCKED,
        )
        for r in rows
    ]


def change_visibility(
    conn: sqlite3.Connection,
    *,
    player_id: int,
    takeaway_public_id: str,
    visibility: str,
    review_scope: str,
) -> None:
    """Change who can read one of the player's own notes (GAME-031, DEC-076).

    Switching between named and anonymous keeps the review status. Sharing a private note sends
    it for review (SAFE-007). A rejected or hidden note can only be made private, and keeps its
    status so it can't be shared again. Raises TakeawayRefused, or GameNotOn while paused or off.
    """
    shared_status = _first_status(visibility, review_scope)
    conn.execute("BEGIN IMMEDIATE")
    try:
        require_game_on(conn)  # DEC-076: blocked like writing a note (GAME-033)
        row = conn.execute(
            "SELECT id, visibility, review_status FROM takeaway"
            " WHERE public_id = ? AND player_id = ?",
            (takeaway_public_id, player_id),
        ).fetchone()
        if row is None:
            raise TakeawayRefused(*NOT_FOUND)  # someone else's note looks like no note
        old = row["review_status"]
        if visibility == row["visibility"]:
            status = old
        elif visibility == "private":
            status = old if old in LOCKED else "not_needed"
        elif old in LOCKED:
            raise TakeawayRefused(*STAY_PRIVATE)
        elif row["visibility"] in SHARED:
            status = old  # DEC-076: named to anonymous or back keeps the review
        else:
            status = shared_status
        if (visibility, status) != (row["visibility"], old):
            fresh = status in ("not_needed", "pending")
            conn.execute(
                "UPDATE takeaway SET visibility = ?, review_status = ?,"
                " reviewed_by = CASE WHEN ? THEN NULL ELSE reviewed_by END,"
                " reviewed_at = CASE WHEN ? THEN NULL ELSE reviewed_at END"
                " WHERE id = ?",
                (visibility, status, fresh, fresh, row["id"]),
            )
            audit.record(
                conn,
                actor_type="player",
                actor_id=player_id,
                action=f"visibility_{visibility}",
                target_type="takeaway",
                target_id=row["id"],
            )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def review(
    conn: sqlite3.Connection, *, admin_id: int, takeaway_public_id: str, outcome: str
) -> None:
    """Approve, reject, or hide a shared note, with an audit row (SAFE-040, SAFE-041, DEC-076).

    Rejecting keeps the note's points (SAFE-040). Raises TakeawayRefused when the note is gone,
    private, or already moved on, for example when another admin pressed first.
    """
    if outcome not in REVIEW_FROM:
        raise TakeawayRefused(
            400, "BAD_INPUT", "Please choose approve, reject, or hide."
        )
    starts = REVIEW_FROM[outcome]
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT id, review_status FROM takeaway WHERE public_id = ? AND visibility <> 'private'",
            (takeaway_public_id,),
        ).fetchone()
        if row is None:
            raise TakeawayRefused(
                *NOT_FOUND
            )  # SAFE-029: private notes are not reviewed
        if row["review_status"] not in starts:
            raise TakeawayRefused(*ALREADY_REVIEWED)
        conn.execute(
            "UPDATE takeaway SET review_status = ?, reviewed_by = ?,"
            " reviewed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (REVIEW_TO[outcome], admin_id, row["id"]),
        )
        audit.record(
            conn,
            actor_type="admin",
            actor_id=admin_id,
            action=f"review_{outcome}",
            target_type="takeaway",
            target_id=row["id"],
        )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def review_queue(conn: sqlite3.Connection, status: str) -> list[ForReview]:
    """Shared notes with this status, oldest first so nothing waits forever (SAFE-007).

    Never private notes (SAFE-029). Always with the author, even when anonymous (SAFE-009).
    """
    if status not in REVIEW_STATUSES:
        raise TakeawayRefused(*NOT_FOUND)
    rows = conn.execute(
        "SELECT t.public_id, s.title, t.text, t.visibility, t.review_status,"
        " p.first_name, p.last_name, c.name AS church"
        " FROM takeaway AS t JOIN session AS s ON s.id = t.session_id"
        " JOIN player AS p ON p.id = t.player_id JOIN church AS c ON c.id = p.church_id"
        " WHERE t.visibility <> 'private' AND t.review_status = ? ORDER BY t.id",
        (status,),
    ).fetchall()
    return [
        ForReview(
            r["public_id"],
            r["title"],
            r["text"],
            r["visibility"],
            r["review_status"],
            r["first_name"],
            r["last_name"],
            r["church"],
        )
        for r in rows
    ]


def review_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many shared notes have each review status, for the review page tabs (SAFE-029)."""
    counts = dict.fromkeys(REVIEW_STATUSES, 0)
    for r in conn.execute(
        "SELECT review_status, count(*) AS n FROM takeaway"
        " WHERE visibility <> 'private' GROUP BY review_status"
    ):
        counts[r["review_status"]] = r["n"]
    return counts


def list_approved(conn: sqlite3.Connection) -> list[SharedNote]:
    """Approved shared notes for the Summary page, newest session first (UI-038, SAFE-007).

    Named notes carry first name and church only. Anonymous ones carry neither (SAFE-009, SAFE-028).
    """
    rows = conn.execute(
        "SELECT s.title, t.text, t.visibility, p.first_name, c.name AS church"
        " FROM takeaway AS t JOIN session AS s ON s.id = t.session_id"
        " JOIN player AS p ON p.id = t.player_id JOIN church AS c ON c.id = p.church_id"
        " WHERE t.visibility <> 'private' AND t.review_status = 'approved'"
        " ORDER BY s.ended_at DESC, s.id DESC, t.id DESC",
    ).fetchall()
    return [
        SharedNote(r["title"], r["text"], r["first_name"], r["church"])
        if r["visibility"] == "shared_named"
        else SharedNote(r["title"], r["text"], None, None)
        for r in rows
    ]


# ENG-113, AI-047: shared notes for the PR preview, so Review and Summary have something to show.
# Written by the leaderboard preview players. Obviously fake (SAFE-031).
PREVIEW_NOTES = (
    (
        ("Test", "Player 3"),
        "shared_named",
        "approved",
        "Example takeaway: I want to listen first this week and ask more questions in small group.",
    ),
    (
        ("Test", "Player 4"),
        "shared_anonymous",
        "approved",
        "Example takeaway: showing up for my friends matters more than having the right words.",
    ),
    (
        ("Test", "Player 5"),
        "shared_named",
        "pending",
        "Example takeaway: serving doesn't need a stage. I'll help set up before youth group.",
    ),
    (
        ("Test", "Player 6"),
        "shared_anonymous",
        "pending",
        "Example takeaway: I can pray for one person by name every morning this month.",
    ),
)


def seed_preview(conn: sqlite3.Connection, session_title: str) -> list[str]:
    """Adds PREVIEW_NOTES to the ended preview session, once (ENG-113, AI-047).

    Skips a writer who wasn't made (no preview PIN set) or already has a note there. Seeded notes
    earn no points, so the leaderboard preview stays as it was.
    """
    session = conn.execute(
        "SELECT id FROM session WHERE title = ?", (session_title,)
    ).fetchone()
    if session is None:
        return []
    admin = conn.execute(
        "SELECT id FROM staff_account WHERE role = 'admin' ORDER BY id LIMIT 1"
    ).fetchone()
    added = []
    for (first, last), visibility, status, text in PREVIEW_NOTES:
        player = conn.execute(
            "SELECT id FROM player WHERE first_name = ? AND last_name = ?",
            (first, last),
        ).fetchone()
        if (
            player is None
            or conn.execute(
                "SELECT 1 FROM takeaway WHERE player_id = ? AND session_id = ?",
                (player["id"], session["id"]),
            ).fetchone()
        ):
            continue
        reviewed = status == "approved" and admin is not None
        conn.execute(
            "INSERT INTO takeaway (player_id, session_id, text, visibility, review_status,"
            " reviewed_by, reviewed_at) VALUES (?, ?, ?, ?, ?, ?,"
            " CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%SZ', 'now') END)",
            (
                player["id"],
                session["id"],
                text,
                visibility,
                status,
                admin["id"] if reviewed else None,
                reviewed,
            ),
        )
        added.append(f"{first} {last}")
    return added
