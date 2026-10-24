"""The logged-in player. A stub until Join, PIN set, and log in is built (ARCH-032, ARCH-034)."""

from dataclasses import dataclass


class LoginRequired(Exception):
    pass


@dataclass(frozen=True)
class CurrentPlayer:
    public_id: str  # ARCH-020, DATA-003: random, never a row number or a name
    score: int


def get_current_player() -> CurrentPlayer:
    # No login exists yet, so nobody is logged in. Tests override this dependency.
    raise LoginRequired
