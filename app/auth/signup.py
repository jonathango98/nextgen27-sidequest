"""Sign-up: check the Join form and save the player (SAFE-002, SAFE-021, ARCH-033)."""

import secrets
import sqlite3
import string
from dataclasses import dataclass

from app.auth import pin as pins
from app.services import points
from app.services.game_state import GAME_NOT_ON_MESSAGES, GameNotOn

# Not game numbers: input limits that keep junk out of the database.
NAME_MAX_CHARS = 50
PUBLIC_ID_CHARS = string.ascii_lowercase + string.digits
PUBLIC_ID_LENGTH = 12  # ARCH-020: random and opaque, about 62 bits


class SignupError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message


def _bad_input(message: str) -> SignupError:
    return SignupError(400, "BAD_INPUT", message)


def _name_taken_error() -> SignupError:
    # ARCH-033, DEC-033
    return SignupError(
        409,
        "NAME_TAKEN",
        "Someone from your church already joined with this name. "
        "Please find an usher at the game booth.",
    )


@dataclass(frozen=True)
class Details:
    first_name: str
    last_name: str
    church_id: int
    is_under_18: bool


def clean_name(value: str) -> str:
    # DATA-016: no spaces at either end. Inner runs of spaces count as one.
    return " ".join(value.split())


def churches(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, name FROM church ORDER BY name").fetchall()


def check_details(conn: sqlite3.Connection, form: dict[str, str]) -> Details:
    """SAFE-002: exactly these fields. Anything else in the form is ignored."""
    first = clean_name(form.get("first_name", ""))
    last = clean_name(form.get("last_name", ""))
    if not first:
        raise _bad_input("Please enter your first name.")
    if not last:
        raise _bad_input("Please enter your last name.")
    if len(first) > NAME_MAX_CHARS or len(last) > NAME_MAX_CHARS:
        raise _bad_input(f"Please keep each name under {NAME_MAX_CHARS} letters.")
    church = form.get("church_id", "")
    row = None
    if church.isascii() and church.isdigit():
        row = conn.execute(
            "SELECT id FROM church WHERE id = ?", (int(church),)
        ).fetchone()
    if row is None:
        raise _bad_input("Please pick your church.")
    # DEC-034: the question is "Are you 18 or older?", so "no" means under 18.
    age_18_plus = form.get("age_18_plus")
    if age_18_plus not in ("yes", "no"):
        raise _bad_input("Please answer whether you're 18 or older.")
    details = Details(first, last, row["id"], age_18_plus == "no")
    if _name_taken(conn, details):
        raise _name_taken_error()
    return details


def _name_taken(conn: sqlite3.Connection, d: Details) -> bool:
    # Same comparison as the DATA-016 index.
    return (
        conn.execute(
            "SELECT 1 FROM player WHERE church_id = ?"
            " AND first_name = ? COLLATE NOCASE AND last_name = ? COLLATE NOCASE",
            (d.church_id, d.first_name, d.last_name),
        ).fetchone()
        is not None
    )


def check_pin(form: dict[str, str], digits: int) -> str:
    pin, again = form.get("pin", ""), form.get("pin_again", "")
    if not pins.is_valid(pin, digits):
        raise _bad_input(f"Your PIN needs to be {digits} numbers.")
    if pin != again:
        raise _bad_input("Those two PINs don't match. Please try again.")
    return pin


def create_player(conn: sqlite3.Connection, d: Details, pin: str, config: dict) -> str:
    """Saves the player and their join points together, and returns their public ID."""
    # Hash first: it is slow on purpose, and the lock below would make other joiners wait.
    pin_hash = pins.hash_pin(pin)
    # ARCH-013: IMMEDIATE takes the write lock first, so two sign-ups queue instead of racing.
    conn.execute("BEGIN IMMEDIATE")
    try:
        public_id, player_id = _insert_player(conn, d, pin_hash)
        points.award_join(
            conn,
            player_id=player_id,
            amount=config["points"]["join"],
            while_paused=config["join"]["points_while_paused"],
        )
    except GameNotOn as error:
        conn.execute("ROLLBACK")
        # GAME-108: sign-up is closed while the game is off, and nothing is saved.
        raise SignupError(
            423, error.error_code, GAME_NOT_ON_MESSAGES[error.error_code]
        ) from error
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return public_id


def _insert_player(
    conn: sqlite3.Connection, d: Details, pin_hash: str
) -> tuple[str, int]:
    while True:
        public_id = "".join(
            secrets.choice(PUBLIC_ID_CHARS) for _ in range(PUBLIC_ID_LENGTH)
        )
        try:
            player_id = conn.execute(
                "INSERT INTO player"
                " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    public_id,
                    d.first_name,
                    d.last_name,
                    d.church_id,
                    int(d.is_under_18),
                    pin_hash,
                ),
            ).lastrowid
            return public_id, player_id
        except sqlite3.IntegrityError as error:
            if "player.public_id" in str(error):
                continue  # DATA-003: astronomically rare, pick another
            if _name_taken(conn, d):
                raise _name_taken_error() from error  # DATA-016: two phones joined at the same moment
            raise
