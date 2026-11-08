"""Home and Open Box show real blind box numbers (home.pages).

GAME-070, GAME-071, GAME-073, GAME-074, GAME-077, UI-036, UI-051.
Every score is built from game-config.yaml, never hardcoded (AI-013).
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.services import qr
from tests.conftest import seed_fake_players

FAKE_QR_KEY = "test-only-fake-signing-key"  # never a real key (SAFE-030)
PUBLIC_ID = "testpid01"  # Test Player 1, fake data (ENG-047)
BOX = load_config()["blind_box"]
STEP = BOX["milestone_points"]
MAX = BOX["max_per_player"]


def page_text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "side-quest.db"))
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    with TestClient(create_app(), base_url="https://testserver") as c:
        seed_fake_players(c.app.state.db_path, PUBLIC_ID)
        yield c


def _as(client, score):
    client.app.dependency_overrides[get_current_player] = lambda: CurrentPlayer(
        public_id=PUBLIC_ID, score=score
    )


def _bar(html):
    return re.search(r'<div class="progress-track"[^>]*>', html).group(0)


def test_game_070_home_bar_shows_points_since_last_milestone(client):
    since = STEP // 3
    _as(client, STEP + since)
    html = client.get("/").text
    assert f"{since} / {STEP}" in page_text(html)
    assert f'aria-valuenow="{since}"' in _bar(html)
    assert f"width: {since * 100 // STEP}%" in html


def test_game_070_home_bar_goes_up_with_score(client):
    _as(client, 0)
    before = client.get("/").text
    _as(client, STEP // 2)
    after = client.get("/").text
    assert 'aria-valuenow="0"' in _bar(before)
    assert f'aria-valuenow="{STEP // 2}"' in _bar(after)


def test_game_071_home_says_all_boxes_earned_at_the_max(client):
    _as(client, (MAX + 1) * STEP)
    html = client.get("/").text
    text = page_text(html)
    # UI-051: the full bar says so in words, and never shows a next box that does not exist.
    assert "All boxes earned" in text
    assert "Next box" not in text
    assert "width: 100%" in html
    assert 'aria-valuetext="All boxes earned"' in _bar(html)


def test_game_074_open_box_shows_boxes_ready_to_claim(client):
    earned = MAX - 1
    _as(client, earned * STEP)
    html = client.get("/box").text
    assert f'<p class="page-sub">{earned} ready</p>' in html
    labels = re.findall(r'<span class="box-label">([^<]+)</span>', html)
    assert labels[:earned] == ["Ready"] * earned
    assert labels[earned:] == [f"{n * STEP} pts" for n in range(earned + 1, MAX + 1)]


def test_game_071_open_box_never_more_ready_than_the_max(client):
    _as(client, (MAX + 2) * STEP)
    html = client.get("/box").text
    assert f'<p class="page-sub">{MAX} ready</p>' in html
    assert html.count("box-tile box-ready") == MAX


def test_game_073_opening_open_box_saves_nothing(client):
    _as(client, MAX * STEP)
    tables = ("point_ledger", "audit_log")

    def counts():
        conn = connect(client.app.state.db_path)
        try:
            return [
                conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables
            ]
        finally:
            conn.close()

    before = counts()
    assert client.get("/box").status_code == 200
    assert client.get("/box").status_code == 200
    assert counts() == before
    # Opening it twice still shows the same boxes: nothing was used up.
    assert f'<p class="page-sub">{MAX} ready</p>' in client.get("/box").text


@pytest.mark.parametrize("score", [0, STEP, MAX * STEP])
def test_game_077_no_boxes_left_counter_at_any_score(client, score):
    _as(client, score)
    for path in ("/", "/box"):
        assert "left" not in page_text(client.get(path).text).lower(), path
