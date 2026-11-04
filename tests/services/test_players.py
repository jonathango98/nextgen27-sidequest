import pytest
from fastapi.testclient import TestClient

from app.auth import session
from app.config import load_config
from app.db import connect, migrate
from app.main import create_app
from app.services import churches, players, qr
from tests.conftest import make_fake_pin

# Fake data only (ENG-047, SAFE-030).
CONFIG = load_config()
FAKE_PIN = make_fake_pin(CONFIG["auth"]["pin_digits"])


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "players.db")
    migrate(connection)
    churches.seed_examples(connection)
    yield connection
    connection.close()


def _players(conn):
    return conn.execute(
        "SELECT first_name, last_name, is_under_18, pin_hash, church.name AS church"
        " FROM player JOIN church ON church.id = player.church_id"
    ).fetchall()


def test_eng_113_preview_seed_adds_test_player_with_join_points(conn, monkeypatch):
    monkeypatch.setenv(players.PREVIEW_PIN_ENV, FAKE_PIN)
    assert players.seed_preview(conn, CONFIG) == ["Test Player 1"]
    [row] = _players(conn)
    assert (row["first_name"], row["last_name"]) == players.PREVIEW_PLAYER
    assert row["church"] == churches.EXAMPLE_CHURCHES[0]
    [points] = conn.execute("SELECT amount FROM point_ledger").fetchall()
    assert points["amount"] == CONFIG["points"]["join"]


def test_ai_047_preview_seed_is_never_a_minor(conn, monkeypatch):
    monkeypatch.setenv(players.PREVIEW_PIN_ENV, FAKE_PIN)
    players.seed_preview(conn, CONFIG)
    assert _players(conn)[0]["is_under_18"] == 0


def test_safe_030_preview_seed_skips_without_a_pin(conn, monkeypatch):
    monkeypatch.delenv(players.PREVIEW_PIN_ENV, raising=False)
    assert players.seed_preview(conn, CONFIG) == []
    assert _players(conn) == []


def test_safe_021_preview_seed_skips_a_pin_of_the_wrong_shape(conn, monkeypatch):
    monkeypatch.setenv(players.PREVIEW_PIN_ENV, FAKE_PIN + "0")
    assert players.seed_preview(conn, CONFIG) == []
    assert _players(conn) == []


def test_eng_113_preview_seed_never_changes_an_existing_player(conn, monkeypatch):
    monkeypatch.setenv(players.PREVIEW_PIN_ENV, FAKE_PIN)
    players.seed_preview(conn, CONFIG)
    before = _players(conn)[0]["pin_hash"]
    monkeypatch.setenv(players.PREVIEW_PIN_ENV, make_fake_pin(len(FAKE_PIN), start=5))
    assert players.seed_preview(conn, CONFIG) == []
    [row] = _players(conn)
    assert row["pin_hash"] == before
    assert not conn.in_transaction


def test_eng_113_preview_seed_skips_without_the_example_church(tmp_path, monkeypatch):
    monkeypatch.setenv(players.PREVIEW_PIN_ENV, FAKE_PIN)
    connection = connect(tmp_path / "no-church.db")
    migrate(connection)
    assert players.seed_preview(connection, CONFIG) == []
    connection.close()


@pytest.mark.parametrize(
    ("environment", "seeded"),
    # A preview gets Test Player 1, Test Player 2 for the connections.meet hand test,
    # and Test Player 3 for the connections.answers hand test.
    [("sidequest-pr-68", 3), ("staging", 0), ("production", 0), (None, 0)],
)
def test_arch_017_app_start_seeds_the_player_only_on_pr_previews(
    tmp_path, monkeypatch, environment, seeded
):
    db = tmp_path / "start.db"
    monkeypatch.setenv("SQ_DB_PATH", str(db))
    monkeypatch.setenv(session.KEY_ENV, "test-only-fake-session-key")
    monkeypatch.setenv(qr.KEY_ENV, "test-only-fake-signing-key")
    monkeypatch.setenv(players.PREVIEW_PIN_ENV, FAKE_PIN)
    if environment is None:
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    else:
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", environment)
    with TestClient(create_app()):
        pass
    connection = connect(db)
    assert connection.execute("SELECT COUNT(*) FROM player").fetchone()[0] == seeded
    connection.close()
