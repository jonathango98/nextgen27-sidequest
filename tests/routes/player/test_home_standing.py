import math
import re
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from app.auth.current import CurrentPlayer, get_current_player
from app.db import connect
from app.main import create_app
from app.services import points, qr
from tests.conftest import seed_fake_players

FAKE_QR_KEY = "test-only-fake-signing-key"  # never a real key (SAFE-030)


def page_text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Own database per test, so the ranking only holds this test's players.
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "side-quest.db"))
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    with TestClient(create_app(), base_url="https://testserver") as c:
        yield c


def _switch(client, on):
    # GAME-085: only this test's app sees the switch turned on.
    cfg = client.app.state.config
    client.app.state.config = {
        **cfg,
        "leaderboard": {**cfg["leaderboard"], "in_app_leaderboard": on},
    }


def _crowd(client):
    """Fake Test Player 1, 2, ... in places 1, 2, ... (ENG-047). Returns the crowd size."""
    cfg = client.app.state.config
    lb = cfg["leaderboard"]
    size = 2 * (lb["in_app_rank_top_n"] * 100 // lb["in_app_percent_cutoff"] + 1)
    public_ids = [f"testpid{n:02}" for n in range(1, size + 1)]
    ids = seed_fake_players(client.app.state.db_path, *public_ids)
    conn = connect(client.app.state.db_path)
    try:
        for n, public_id in enumerate(public_ids, start=1):
            points.award_join(
                conn,
                player_id=ids[public_id],
                amount=cfg["points"]["join"],
                while_paused=True,
            )
            points.award(
                conn,
                player_id=ids[public_id],
                reason_code="booth_visit",
                amount=(size - n + 1) * cfg["points"]["booth_visit"],
                source_type="booth",
                source_id=1,
            )
    finally:
        conn.close()
    return size


def _home_as(client, place):
    client.app.dependency_overrides[get_current_player] = lambda: CurrentPlayer(
        public_id=f"testpid{place:02}", score=0
    )
    response = client.get("/")
    assert response.status_code == 200
    return page_text(response.text)


def test_game_085_home_shows_no_standing_with_the_switch_off(client):
    _crowd(client)
    _switch(client, False)
    assert "You're" not in _home_as(client, 1)


def test_game_085_home_shows_a_top_place(client):
    _crowd(client)
    _switch(client, True)
    assert "You're #1" in _home_as(client, 1)


def test_game_085_home_shows_top_percent_below_the_top_places(client):
    size = _crowd(client)
    _switch(client, True)
    place = client.app.state.config["leaderboard"]["in_app_rank_top_n"] + 1
    percent = math.ceil(Fraction(place * 100, size))
    assert f"You're in the top {percent}%" in _home_as(client, place)


def test_game_085_home_shows_nothing_in_the_bottom_half(client):
    size = _crowd(client)
    _switch(client, True)
    assert "You're" not in _home_as(client, size)
