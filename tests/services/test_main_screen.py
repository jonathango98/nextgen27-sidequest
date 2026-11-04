import sqlite3

import pytest

from app.db import connect, migrate
from app.services import main_screen
from app.services.game_state import set_state

FAKE_ADMIN_ID = 7  # fake staff id (ENG-047)


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


def _actions(conn):
    return [r["action"] for r in conn.execute("SELECT action FROM audit_log")]


def test_ui_044_off_view_starts_as_offline(conn):
    assert main_screen.off_view(conn) == "offline"


def test_ui_044_database_refuses_an_unknown_off_view(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE game_state SET screen_off_view = 'leaderboard'")


def test_ui_044_admin_switch_saves_with_one_audit_row(conn):
    assert main_screen.change_off_view(conn, "recap", FAKE_ADMIN_ID) is True
    assert main_screen.off_view(conn) == "recap"
    # Picking the view already shown changes nothing and writes nothing (ARCH-050).
    assert main_screen.change_off_view(conn, "recap", FAKE_ADMIN_ID) is False
    main_screen.change_off_view(conn, "offline", FAKE_ADMIN_ID)
    assert _actions(conn) == ["screen_off_recap", "screen_off_offline"]


def test_ui_044_unknown_off_view_is_refused(conn):
    with pytest.raises(main_screen.UnknownOffView):
        main_screen.change_off_view(conn, "leaderboard", FAKE_ADMIN_ID)
    assert _actions(conn) == []


def test_ui_040_views_take_turns_and_wrap_around():
    seen = [main_screen.VIEWS[0]]
    for _ in main_screen.VIEWS:
        seen.append(main_screen.next_view(seen[-1]))
    assert seen[: len(main_screen.VIEWS)] == list(main_screen.VIEWS)
    assert seen[-1] == main_screen.VIEWS[0]


@pytest.mark.parametrize("state", ["on", "paused"])
def test_dec_069_pause_does_not_stop_the_main_screen(conn, state):
    set_state(conn, state)
    assert main_screen.showing(conn, "churches") == "churches"


def test_ui_040_off_shows_the_off_view(conn):
    set_state(conn, "off")
    assert main_screen.showing(conn, "churches") == "offline"
    main_screen.change_off_view(conn, "recap", FAKE_ADMIN_ID)
    assert main_screen.showing(conn, "churches") == "recap"
