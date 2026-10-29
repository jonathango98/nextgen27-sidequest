import re
import sqlite3
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.config import load_config
from app.db import MIGRATIONS_DIR, connect, get_db, migrate
from app.main import create_app
from app.services.game_state import (
    GameNotOn,
    current_state,
    require_game_on,
    set_state,
)

MIGRATION = "0002_create_game_state.sql"


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Own database per test, so a state change never leaks into other tests.
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "side-quest.db"))
    app = create_app()

    # Stands in for an earning action until points.ledger adds the real ones.
    @app.post("/test-earn")
    def earn(db: Annotated[sqlite3.Connection, Depends(get_db)]):
        require_game_on(db)
        return {"earned": True}

    with TestClient(app) as client:
        yield client


def _set(client, state):
    db = connect(client.app.state.db_path)
    try:
        set_state(db, state)
    finally:
        db.close()


def test_game_100_states_match_config():
    # The SQL check can't read the config, so this keeps the two in step (ARCH-043).
    sql = (MIGRATIONS_DIR / MIGRATION).read_text(encoding="utf-8")
    allowed = re.search(r"state IN \(([^)]*)\)", sql).group(1)
    assert re.findall(r"'([a-z]+)'", allowed) == load_config()["game"]["states"]


def test_data_013_game_state_has_exactly_one_row(conn):
    assert conn.execute("SELECT count(*) FROM game_state").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO game_state (id, state) VALUES (2, 'on')")


def test_data_013_rejects_unknown_state(conn):
    with pytest.raises(sqlite3.IntegrityError):
        set_state(conn, "sleeping")
    assert current_state(conn) == "on"


@pytest.mark.parametrize("state", load_config()["game"]["states"])
def test_game_100_every_state_can_be_set(conn, state):
    set_state(conn, state)
    assert current_state(conn) == state


def test_game_100_set_state_records_who_and_when(conn):
    set_state(conn, "paused", updated_by=7)
    row = conn.execute("SELECT updated_by, updated_at FROM game_state").fetchone()
    assert row["updated_by"] == 7
    assert row["updated_at"]


def test_arch_041_require_game_on_refuses_when_paused(conn):
    set_state(conn, "paused")
    with pytest.raises(GameNotOn) as caught:
        require_game_on(conn)
    assert caught.value.error_code == "PAUSED"


def test_game_100_earning_works_when_on(client):
    response = client.post("/test-earn")
    assert response.status_code == 200
    assert response.json() == {"earned": True}


def test_api_020_paused_returns_423_paused(client):
    _set(client, "paused")
    response = client.post("/test-earn")
    assert response.status_code == 423
    assert 'data-error-code="PAUSED"' in response.text
    assert "The game is paused during the session." in response.text


def test_game_108_off_returns_423_game_off(client):
    _set(client, "off")
    response = client.post("/test-earn")
    assert response.status_code == 423
    assert 'data-error-code="GAME_OFF"' in response.text
    assert "The game is closed right now." in response.text


def test_arch_042_new_state_applies_to_next_request(client):
    assert client.post("/test-earn").status_code == 200
    _set(client, "paused")
    assert client.post("/test-earn").status_code == 423
    _set(client, "on")
    assert client.post("/test-earn").status_code == 200


def test_game_102_reading_pages_still_work_when_paused(client):
    _set(client, "paused")
    assert client.get("/health").status_code == 200
