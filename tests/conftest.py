import os

import pytest

from app.config import load_config


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
