import os

import pytest


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
