"""Log in on another phone (ARCH-032), with lockout after too many wrong PINs (SAFE-022)."""

import sqlite3
from functools import cache

from app.auth import pin as pins
from app.auth.signup import clean_name


class LoginError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message


def _missing() -> LoginError:
    return LoginError(400, "BAD_INPUT", "Please fill in your name, church, and PIN.")


def _no_match() -> LoginError:
    # The same message for an unknown name and a wrong PIN, so it never says who has joined.
    return LoginError(
        400,
        "BAD_INPUT",
        "We couldn't log you in with that name, church, and PIN. Please check them and try again.",
    )


def _locked() -> LoginError:
    # API-021: 403, not 423, so 423 always means the game is not on.
    return LoginError(
        403,
        "PIN_LOCKED",
        "This account is locked. Please find an admin at the game booth.",
    )


@cache
def _dummy_hash() -> str:
    return pins.hash_pin("0")


def log_in(conn: sqlite3.Connection, form: dict[str, str], auth: dict) -> str:
    """Checks name, church, and PIN. Returns the player's public ID."""
    first = clean_name(form.get("first_name", ""))
    last = clean_name(form.get("last_name", ""))
    church = form.get("church_id", "")
    pin = form.get("pin", "")
    if not (first and last and church.isascii() and church.isdigit()):
        raise _missing()
    if not pins.is_valid(pin, auth["pin_digits"]):
        raise _no_match()

    row = conn.execute(
        "SELECT id, public_id, pin_hash, locked_at FROM player WHERE church_id = ?"
        " AND first_name = ? COLLATE NOCASE AND last_name = ? COLLATE NOCASE",
        (int(church), first, last),
    ).fetchone()
    if row is None:
        # Same work as a real check, so the response time says nothing about who has joined.
        pins.verify_pin(pin, _dummy_hash())
        raise _no_match()
    if row["locked_at"] is not None:
        raise _locked()

    # SAFE-022: take one try before checking the PIN, in one statement. Guesses sent all at once
    # then still get at most pin_max_attempts checks.
    reserved = conn.execute(
        "UPDATE player SET failed_pin_attempts = failed_pin_attempts + 1"
        " WHERE id = ? AND locked_at IS NULL AND failed_pin_attempts < ?"
        " RETURNING failed_pin_attempts",
        (row["id"], auth["pin_max_attempts"]),
    ).fetchall()
    if not reserved:
        raise _locked()

    if pins.verify_pin(pin, row["pin_hash"]):
        conn.execute(
            "UPDATE player SET failed_pin_attempts = 0 WHERE id = ?", (row["id"],)
        )
        return row["public_id"]

    if reserved[0]["failed_pin_attempts"] >= auth["pin_max_attempts"]:
        conn.execute(
            "UPDATE player SET locked_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"
            " WHERE id = ? AND locked_at IS NULL",
            (row["id"],),
        )
        raise _locked()
    raise _no_match()
