"""Blind box math, worked out from score every time (GAME-070, GAME-071, GAME-074, DATA-031).

Nothing here is stored. Every number comes from the `blind_box` section of
game-config.yaml (AI-013, ENG-031), passed in as `cfg`.
"""

import sqlite3
from dataclasses import dataclass

from app.services import churches, players, points
from app.services.game_state import GameNotOn

# ENG-113: a fake adult a PR preview adds, past the first box milestone, so testers see a
# Ready box on Open Box and a part-full bar on Home (AI-047). The other preview players
# stay below the first milestone.
PREVIEW_PLAYER = ("Test", "Player 7")
PREVIEW_REASON = "preview_box_example"


def earned(score: int, cfg: dict) -> int:
    """Blind boxes earned from score: one per milestone, capped at the max (GAME-070, GAME-071).

    A score below 0 after an admin revocation earns none.
    """
    boxes = max(score, 0) // cfg["milestone_points"]
    return min(boxes, cfg["max_per_player"])


def claimable(earned_boxes: int, claimed_boxes: int) -> int:
    """Blind boxes the player can claim now, never below 0 (GAME-074)."""
    return max(earned_boxes - claimed_boxes, 0)


def claimed_count(conn: sqlite3.Connection, public_id: str) -> int:
    """Blind boxes already handed to this player at the game booth (GAME-073).

    Always 0 for now: the BoxClaim table and the usher's claim button come with
    the `blind-box.handout` piece (DATA-026), which replaces this with a count.
    """
    return 0


@dataclass(frozen=True)
class Progress:
    """Where a player stands on the way to the next blind box (GAME-070, UI-051)."""

    points: int  # points since the last milestone
    milestone: int  # points between two blind boxes
    all_earned: bool  # every box is earned, so there is no next box (GAME-071)

    @property
    def percent(self) -> int:
        """How full the bar is, 0 to 100."""
        if self.all_earned:
            return 100
        return self.points * 100 // self.milestone


def progress(score: int, cfg: dict) -> Progress:
    """Points since the last milestone, for example 120 of 300 (GAME-070)."""
    milestone = cfg["milestone_points"]
    if earned(score, cfg) >= cfg["max_per_player"]:
        return Progress(points=milestone, milestone=milestone, all_earned=True)
    return Progress(
        points=max(score, 0) % milestone, milestone=milestone, all_earned=False
    )


def seed_preview(conn: sqlite3.Connection, config: dict) -> list[str]:
    """Adds PREVIEW_PLAYER with points past the first milestone, once (ENG-113, AI-047).

    The points go through the points service, with audit rows (AI-041). Nothing is given
    while the game is paused or off, and a restart gives nothing twice.
    """
    church_name = churches.EXAMPLE_CHURCHES[1]
    added = players.seed_preview_player(conn, config, PREVIEW_PLAYER, church_name)
    player = conn.execute(
        "SELECT p.id FROM player p JOIN church c ON c.id = p.church_id"
        " WHERE p.first_name = ? AND p.last_name = ? AND c.name = ?",
        (*PREVIEW_PLAYER, church_name),
    ).fetchone()
    if player is None:
        return added  # no preview PIN set, so the player wasn't made
    step = config["blind_box"]["milestone_points"]
    try:
        points.award(
            conn,
            player_id=player["id"],
            reason_code=PREVIEW_REASON,
            amount=step + step // 3,
            source_type="player",
            source_id=player["id"],
        )
    except points.AlreadyAwarded, GameNotOn:
        pass
    return added
