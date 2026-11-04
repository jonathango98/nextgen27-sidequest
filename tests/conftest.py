import os

import pytest

from app.config import load_config
from app.db import connect, migrate


@pytest.fixture(scope="session", autouse=True)
def test_db_path(tmp_path_factory):
    # The app refuses to start without SQ_DB_PATH (ARCH-010). Tests use a throwaway file.
    path = tmp_path_factory.mktemp("db") / "test.db"
    old = os.environ.get("SQ_DB_PATH")
    os.environ["SQ_DB_PATH"] = str(path)
    yield path
    if old is None:
        os.environ.pop("SQ_DB_PATH", None)
    else:
        os.environ["SQ_DB_PATH"] = old


@pytest.fixture
def cfg_auth():
    return load_config()["auth"]


def make_fake_pin(digits: int, start: int = 4) -> str:
    # Fake PIN with the configured length (AI-013: never hardcode pin_digits).
    return "".join(str((start + 7 * i) % 10) for i in range(digits))


@pytest.fixture
def fake_pin(cfg_auth):
    return make_fake_pin(cfg_auth["pin_digits"])


def seed_fake_players(path, *public_ids) -> dict[str, int]:
    """A migrated database with Test Player 1, 2, ... in Example Church A (ENG-047).

    Returns each public id's row id, for pages that read the logged-in player's rows.
    """
    conn = connect(path)
    try:
        migrate(conn)
        conn.execute("INSERT OR IGNORE INTO church (name) VALUES ('Example Church A')")
        church = conn.execute(
            "SELECT id FROM church WHERE name = 'Example Church A'"
        ).fetchone()[0]
        ids = {}
        for n, public_id in enumerate(public_ids, start=1):
            conn.execute(
                "INSERT OR IGNORE INTO player"
                " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
                " VALUES (?, 'Test', ?, ?, 0, 'not-a-real-hash')",
                (public_id, f"Player {n}", church),
            )
            ids[public_id] = conn.execute(
                "SELECT id FROM player WHERE public_id = ?", (public_id,)
            ).fetchone()[0]
        return ids
    finally:
        conn.close()
