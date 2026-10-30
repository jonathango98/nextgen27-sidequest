"""The logged-in player, read from the signed session cookie (ARCH-034)."""

from dataclasses import dataclass

from fastapi import Request

from app.auth.session import session_public_id
from app.db import connect
from app.services import points


class LoginRequired(Exception):
    pass


@dataclass(frozen=True)
class CurrentPlayer:
    public_id: str  # ARCH-020, DATA-003: random, never a row number or a name
    score: int


def get_current_player(request: Request) -> CurrentPlayer:
    public_id = session_public_id(request)
    if public_id is None:
        raise LoginRequired
    conn = connect(request.app.state.db_path)
    try:
        row = conn.execute(
            "SELECT id, public_id FROM player WHERE public_id = ?", (public_id,)
        ).fetchone()
        if row is None:
            raise LoginRequired
        # DATA-030: score is the PointLedger sum, read fresh on every page.
        return CurrentPlayer(
            public_id=row["public_id"], score=points.score(conn, row["id"])
        )
    finally:
        conn.close()
