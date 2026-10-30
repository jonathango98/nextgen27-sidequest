"""Usher and admin accounts (ARCH-035, ARCH-036).

Usage: SQ_FIRST_ADMIN_PASSWORD=... python -m app.services.staff create-admin <username>

Makes the very first admin when the game is set up. Later accounts are made by an admin (staff.manage).
The password comes only from the environment, never the command line, so it stays out of
shell history and the process list. It is never printed (SAFE-030).
"""

import os
import sqlite3
import sys

from app.auth.password import hash_password
from app.db import connect, db_path_from_env, migrate

FIRST_ADMIN_PASSWORD_ENV = "SQ_FIRST_ADMIN_PASSWORD"
# ARCH-035. Screen is a device mode, not an account (ARCH-037).
ROLES = ("usher", "admin")


class StaffAccountError(Exception):
    pass


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
