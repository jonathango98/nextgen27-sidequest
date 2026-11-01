"""Staff log in with a username and password (ARCH-036). No lockout yet (DEC-061)."""

import sqlite3
from functools import cache

from app.auth import password as passwords
from app.auth.login import LoginError

# Matches the length CHECK on staff_account.username (migration 0006). Not a game number.
USERNAME_MAX_CHARS = 64


def _missing() -> LoginError:
    return LoginError(400, "BAD_INPUT", "Please fill in your username and password.")


def _no_match() -> LoginError:
    # The same message for an unknown username, a wrong password, and a switched-off account,
    # so it never says who is staff.
    return LoginError(
        400,
        "BAD_INPUT",
        "We couldn't log you in with that username and password. Please check them and try again.",
    )


@cache
def _dummy_hash() -> str:
    return passwords.hash_password("not a real password")


def log_in_staff(conn: sqlite3.Connection, form: dict[str, str]) -> tuple[int, str]:
    """Checks username and password. Returns the account's id and role."""
    username = form.get("username", "").strip()
    password = form.get("password", "")
    if not (username and password):
        raise _missing()

    # The username column ignores case (migration 0006), so "Test-Admin-1" finds "test-admin-1".
    row = conn.execute(
        "SELECT id, role, password_hash, is_active FROM staff_account WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        # Same work as a real check, so the response time says nothing about who is staff.
        passwords.verify_password(password, _dummy_hash())
        raise _no_match()
    if not passwords.verify_password(password, row["password_hash"]):
        raise _no_match()
    if not row["is_active"]:
        raise _no_match()
    return row["id"], row["role"]
