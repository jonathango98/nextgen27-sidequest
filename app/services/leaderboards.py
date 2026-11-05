"""The main screen leaderboards (GAME-081 to GAME-089, SAFE-004, SAFE-019).

A score is always the sum of the point ledger (DATA-030), so the boards store nothing.
"""

import math
import sqlite3
from dataclasses import dataclass
from fractions import Fraction

from app.services import churches, players, points
from app.services.game_state import GameNotOn

# The only rules this code knows (GAME-089, GAME-084). Any other value in game-config.yaml is
# refused at start, so a config change can't quietly rank by a rule nobody built.
DENOMINATORS = ("active_players",)
TIE_BREAKS = ("first_to_reach",)
# The Mix main screen mockups give each church a dot in one of the six bloom colors in
# tokens.css. The church id picks it, so a church keeps its color on both boards.
DOT_COLORS = 6

# ENG-113: fake adults a PR preview adds, so the boards have something to rank (AI-047). Church A
# gets several players and Church B one big scorer, to show one player can't carry a church.
# The number is how many booth visits worth of example points each one gets.
PREVIEW_REASON = "preview_example"
PREVIEW_PLAYERS = (
    (("Test", "Player 3"), churches.EXAMPLE_CHURCHES[0], 6),
    (("Test", "Player 4"), churches.EXAMPLE_CHURCHES[0], 4),
    (("Test", "Player 5"), churches.EXAMPLE_CHURCHES[0], 2),
    (("Test", "Player 6"), churches.EXAMPLE_CHURCHES[1], 20),
)

# GAME-089: each player's total, their points from anything but joining, and their latest award
# for GAME-084. Players with no ledger rows have nothing to rank.
_TOTALS = (
    "SELECT player_id, sum(amount) AS score,"
    " sum(CASE WHEN reason_code = ? THEN 0 ELSE amount END) AS earned,"
    " max(created_at) AS last_at, max(id) AS last_id"
    " FROM point_ledger GROUP BY player_id"
)


class LeaderboardConfigError(ValueError):
    pass


@dataclass(frozen=True)
class PlayerRow:
    first_name: str
    last_initial: str
    church: str
    dot: int
    score: int


@dataclass(frozen=True)
class ChurchRow:
    church: str
    dot: int
    score: int


@dataclass(frozen=True)
class Standing:
    # GAME-085, DEC-073: one of the two is set. A place in the top places, else a top percent.
    place: int | None = None
    top_percent: int | None = None


def check_config(cfg: dict) -> None:
    if cfg["church_score_denominator"] not in DENOMINATORS:
        raise LeaderboardConfigError(
            f"leaderboard.church_score_denominator must be one of {DENOMINATORS}"
        )
    if cfg["tie_break"] not in TIE_BREAKS:
        raise LeaderboardConfigError(
            f"leaderboard.tie_break must be one of {TIE_BREAKS}"
        )


def top_players(conn: sqlite3.Connection, cfg: dict) -> list[PlayerRow]:
    """The highest scores, at most main_screen_top_n rows (GAME-083).

    Only first name, last initial, and church are read, so a full last name can't reach the
    screen by accident (GAME-086, GAME-088, SAFE-004). Under-18 players are listed like
    everyone else (SAFE-019). A tie goes to whoever reached that score first (GAME-084).
    """
    check_config(cfg)
    rows = conn.execute(
        "SELECT p.first_name, substr(p.last_name, 1, 1) AS last_initial,"
        " c.id AS church_id, c.name AS church, t.score"
        f" FROM ({_TOTALS}) t"
        " JOIN player p ON p.id = t.player_id JOIN church c ON c.id = p.church_id"
        # Same second: the earlier ledger row was saved first. Then the id, so the order is fixed.
        " ORDER BY t.score DESC, t.last_at, t.last_id, p.id LIMIT ?",
        (points.JOIN_REASON, cfg["main_screen_top_n"]),
    ).fetchall()
    return [
        PlayerRow(
            r["first_name"],
            r["last_initial"],
            r["church"],
            r["church_id"] % DOT_COLORS,
            r["score"],
        )
        for r in rows
    ]


def own_standing(
    conn: sqlite3.Connection, cfg: dict, public_id: str
) -> Standing | None:
    """The player's own place for the phone, or None to show nothing (GAME-085, DEC-073).

    Nothing while in_app_leaderboard is off. With it on: the place in the top in_app_rank_top_n,
    else the top percent rounded up down to in_app_percent_cutoff, else nothing. Only the
    player's own standing is read, so no other score can reach a phone (SAFE-028). The order
    is the main screen's, over every player with points (GAME-084).
    """
    if not cfg["in_app_leaderboard"]:
        return None
    check_config(cfg)
    row = conn.execute(
        "SELECT place, total FROM ("
        " SELECT p.public_id,"
        " row_number() OVER (ORDER BY t.score DESC, t.last_at, t.last_id, p.id) AS place,"
        " count(*) OVER () AS total"
        f" FROM ({_TOTALS}) t JOIN player p ON p.id = t.player_id"
        ") WHERE public_id = ?",
        (points.JOIN_REASON, public_id),
    ).fetchone()
    if row is None:
        return None
    if row["place"] <= cfg["in_app_rank_top_n"]:
        return Standing(place=row["place"])
    top_percent = math.ceil(Fraction(row["place"] * 100, row["total"]))
    if top_percent <= cfg["in_app_percent_cutoff"]:
        return Standing(top_percent=top_percent)
    return None


def church_score(
    total: int, players_counted: int, k: int, average: Fraction
) -> Fraction:
    """GAME-089: (their points added up + k x overall average) / (their number + k)."""
    return (total + k * average) / (players_counted + k)


def shown(score: Fraction) -> int:
    # GAME-089: a whole number, with halves rounded up (Python's round() would round 86.5 to 86).
    return math.floor(score + Fraction(1, 2))


def top_churches(conn: sqlite3.Connection, cfg: dict) -> list[ChurchRow]:
    """Churches by shrunk average over active players, at most main_screen_top_n rows.

    Active players have earned points beyond joining (GAME-089, DEC-053). A church needs
    church_min_players of them to appear (GAME-082). Churches are ranked by the exact score and
    shown rounded. An exact tie goes to the church whose counted players reached it first:
    the earlier latest award of any of them (GAME-084).
    """
    check_config(cfg)
    rows = conn.execute(
        "SELECT p.church_id, c.name AS church, t.score, t.last_at, t.last_id"
        f" FROM ({_TOTALS}) t"
        " JOIN player p ON p.id = t.player_id JOIN church c ON c.id = p.church_id"
        " WHERE t.earned > 0",
        (points.JOIN_REASON,),
    ).fetchall()
    if not rows:
        return []
    average = Fraction(sum(r["score"] for r in rows), len(rows))
    by_church: dict[int, dict] = {}
    for r in rows:
        c = by_church.setdefault(
            r["church_id"],
            {"name": r["church"], "total": 0, "count": 0, "last": ("", 0)},
        )
        c["total"] += r["score"]
        c["count"] += 1
        c["last"] = max(c["last"], (r["last_at"], r["last_id"]))
    k = cfg["church_score_prior_players"]
    ranked = sorted(
        (
            (
                -church_score(c["total"], c["count"], k, average),
                c["last"],
                church_id,
                c["name"],
            )
            for church_id, c in by_church.items()
            if c["count"] >= cfg["church_min_players"]
        )
    )
    return [
        ChurchRow(name, church_id % DOT_COLORS, shown(-score))
        for score, _, church_id, name in ranked
    ][: cfg["main_screen_top_n"]]


def seed_preview(conn: sqlite3.Connection, config: dict) -> list[str]:
    """Adds the fake PREVIEW_PLAYERS with example points, once (ENG-113, AI-047).

    The points go through the points service, with audit rows (AI-041). Nothing is given
    while the game is paused or off, and a restart gives nothing twice.
    """
    added = []
    for name, church_name, booth_visits in PREVIEW_PLAYERS:
        added += players.seed_preview_player(conn, config, name, church_name)
        player = conn.execute(
            "SELECT p.id FROM player p JOIN church c ON c.id = p.church_id"
            " WHERE p.first_name = ? AND p.last_name = ? AND c.name = ?",
            (*name, church_name),
        ).fetchone()
        if player is None:
            continue  # no preview PIN set, so the player wasn't made
        try:
            points.award(
                conn,
                player_id=player["id"],
                reason_code=PREVIEW_REASON,
                amount=booth_visits * config["points"]["booth_visit"],
                source_type="player",
                source_id=player["id"],
            )
        except points.AlreadyAwarded, GameNotOn:
            pass
    return added
