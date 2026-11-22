"""Usher and admin accounts (ARCH-035, ARCH-036).

Usage: SQ_FIRST_ADMIN_PASSWORD=... python -m app.services.staff create-admin <username>

Makes the very first admin when the game is set up. Later accounts are made by an admin (staff.manage).
The password comes only from the environment, never the command line, so it stays out of
shell history and the process list. It is never printed (SAFE-030).
"""

import os
import sqlite3
import sys
from dataclasses import dataclass

from app.auth.password import hash_password
from app.db import connect, db_path_from_env, migrate
from app.services import audit

FIRST_ADMIN_PASSWORD_ENV = "SQ_FIRST_ADMIN_PASSWORD"
# ARCH-035. Screen is a device mode, not an account (ARCH-037).
ROLES = ("usher", "admin")
# Not a game number: the database refuses longer usernames (migration 0006).
USERNAME_MAX_CHARS = 64
# Obviously fake (SAFE-031), so a PR preview's staff pages can be tested (ARCH-017).
# Passwords come only from Railway variables, never the repo (SAFE-030).
PREVIEW_ACCOUNTS = (
    ("test-admin-1", "admin", "SQ_PREVIEW_ADMIN_PASSWORD"),
    ("test-usher-1", "usher", "SQ_PREVIEW_USHER_PASSWORD"),
)


class StaffAccountError(Exception):
    pass


class StaffAccountNotFound(Exception):
    pass


@dataclass(frozen=True)
class Account:
    id: int
    username: str
    role: str
    is_active: bool


def create_account(
    conn: sqlite3.Connection, username: str, password: str, role: str
) -> int | None:
    """Saves a new account and returns its id, or None if the username is taken.

    An existing account is never changed, so running the setup command twice is safe.
    """
    username = username.strip()
    if not username:
        raise StaffAccountError("the username is empty")
    if role not in ROLES:
        raise StaffAccountError(f"role must be one of {', '.join(ROLES)}")
    if not password:
        raise StaffAccountError("the password is empty")
    row = conn.execute(
        "INSERT INTO staff_account (username, password_hash, role) VALUES (?, ?, ?)"
        " ON CONFLICT (username) DO NOTHING RETURNING id",
        (username, hash_password(password), role),
    ).fetchone()
    return None if row is None else row["id"]


def list_accounts(conn: sqlite3.Connection) -> list[Account]:
    """Every account, switched on first, then admins before ushers, then by username."""
    rows = conn.execute(
        "SELECT id, username, role, is_active FROM staff_account"
        " ORDER BY is_active DESC, role = 'usher', username COLLATE NOCASE"
    )
    return [
        Account(r["id"], r["username"], r["role"], bool(r["is_active"])) for r in rows
    ]


def _audit(conn: sqlite3.Connection, admin_id: int, action: str, account_id: int):
    # ARCH-051: IDs only, never the username or the password.
    audit.record(
        conn,
        actor_type="admin",
        actor_id=admin_id,
        action=action,
        target_type="staff_account",
        target_id=account_id,
    )


def add_account(
    conn: sqlite3.Connection, username: str, password: str, role: str, admin_id: int
) -> int:
    """An admin adds an usher or admin account (ARCH-036, GAME-110), with an audit row (ARCH-050)."""
    username = username.strip()
    if not username:
        raise StaffAccountError("Please type a username.")
    if len(username) > USERNAME_MAX_CHARS:
        raise StaffAccountError(
            f"Usernames can be up to {USERNAME_MAX_CHARS} characters."
        )
    if not password:
        raise StaffAccountError("Please type a password.")
    if role not in ROLES:
        raise StaffAccountError("Please pick Usher or Admin.")
    conn.execute("BEGIN IMMEDIATE")
    try:
        account_id = create_account(conn, username, password, role)
        if account_id is None:
            raise StaffAccountError(f"There is already an account called {username}.")
        _audit(conn, admin_id, "staff_add", account_id)
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return account_id


def set_active(
    conn: sqlite3.Connection, account_id: int, active: bool, admin_id: int
) -> bool:
    """Switch an account off or back on. Returns whether anything changed (OPS-042, ARCH-050).

    An admin can't switch off their own account. The admin doing this is always switched on,
    so that also means the last admin who can log in is never switched off.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT role, is_active FROM staff_account WHERE id = ?", (account_id,)
        ).fetchone()
        if row is None:
            raise StaffAccountNotFound
        if bool(row["is_active"]) == active:
            conn.execute("ROLLBACK")
            return False
        if not active and account_id == admin_id:
            raise StaffAccountError("You can't switch off your own account.")
        conn.execute(
            "UPDATE staff_account SET is_active = ? WHERE id = ?",
            (int(active), account_id),
        )
        _audit(
            conn,
            admin_id,
            "staff_switch_on" if active else "staff_switch_off",
            account_id,
        )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return True


def seed_preview(conn: sqlite3.Connection) -> list[str]:
    """A PR preview starts with no staff. Adds each test account whose password variable is set."""
    created = []
    for username, role, password_env in PREVIEW_ACCOUNTS:
        password = os.environ.get(password_env)
        if password and create_account(conn, username, password, role) is not None:
            created.append(username)
    return created


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "create-admin":
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    username = argv[1].strip()
    password = os.environ.get(FIRST_ADMIN_PASSWORD_ENV)
    if not password:
        print(
            f"Nothing created: {FIRST_ADMIN_PASSWORD_ENV} is not set.", file=sys.stderr
        )
        return 1
    conn = connect(db_path_from_env())
    try:
        migrate(conn)
        created = create_account(conn, username, password, "admin")
    except StaffAccountError as error:
        print(f"Nothing created: {error}.", file=sys.stderr)
        return 1
    finally:
        conn.close()
    if created is None:
        print(f"An account named {username} already exists. Nothing changed.")
    else:
        print(f"Admin {username} created.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
