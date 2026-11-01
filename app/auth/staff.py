"""The logged-in usher or admin, and the role check on every staff page (ARCH-035, DEC-061)."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request

from app.auth.staff_session import staff_session_id
from app.db import connect

# ARCH-035: which roles may open each kind of staff page. DEC-061: admins can open usher pages too.
ALLOWED = {"usher": ("usher", "admin"), "admin": ("admin",)}


class StaffLoginRequired(Exception):
    pass


class WrongRole(Exception):
    pass


@dataclass(frozen=True)
class CurrentStaff:
    id: int
    username: str
    role: str


def get_current_staff(request: Request) -> CurrentStaff:
    hours = request.app.state.config["auth"]["staff_session_hours"]
    staff_id = staff_session_id(request, hours)
    if staff_id is None:
        raise StaffLoginRequired
    conn = connect(request.app.state.db_path)
    try:
        row = conn.execute(
            "SELECT id, username, role FROM staff_account WHERE id = ? AND is_active = 1",
            (staff_id,),
        ).fetchone()
    finally:
        conn.close()
    # ARCH-036: an account switched off after logging in is logged out on its next page.
    if row is None:
        raise StaffLoginRequired
    return CurrentStaff(id=row["id"], username=row["username"], role=row["role"])


def require_role(page: str) -> Callable[[Request], CurrentStaff]:
    """A FastAPI dependency for a staff page. Checked on the server, never by hiding a button."""
    allowed = ALLOWED[page]

    def check(request: Request) -> CurrentStaff:
        staff = get_current_staff(request)
        if staff.role not in allowed:
            raise WrongRole
        return staff

    return check
