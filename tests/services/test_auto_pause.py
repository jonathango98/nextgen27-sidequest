import pytest

from app.db import connect, migrate
from app.services import sessions
from app.services.game_state import current_state, set_state
from app.services.sessions import Details, add, apply_auto_pause, edit, end, list_all

FAKE_ADMIN_ID = 7  # fake staff id (ENG-047)
# A fake clock in UTC (DATA-004), so the tests never wait. Times are made up (SAFE-031).
START = "2027-03-06T15:30:00Z"
BEFORE = "2027-03-06T15:29:59Z"
AT = START
AFTER = "2027-03-06T15:45:00Z"
LATER_START = "2027-03-06T16:00:00Z"
TOMORROW = "2027-03-07T15:30:00Z"


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


def _add(conn, starts_at=START, title="Example Session 1", now=BEFORE):
    add(conn, Details(title, starts_at, 15), FAKE_ADMIN_ID, now=now)
    return next(s for s in list_all(conn) if s.title == title)


def _tick(conn, now, enabled=True):
    return apply_auto_pause(conn, now, enabled)


def _audit(conn):
    return [
        tuple(r)
        for r in conn.execute(
            "SELECT actor_type, actor_id, action, target_type, target_id"
            " FROM audit_log WHERE action = 'auto_pause'"
        )
    ]


def test_game_107_pauses_at_start_time_when_on(conn):
    session = _add(conn)
    assert _tick(conn, BEFORE) is False
    assert current_state(conn) == "on"
    assert _tick(conn, AT) is True
    assert current_state(conn) == "paused"
    # ARCH-050: written as the system, against the session that started.
    assert _audit(conn) == [("system", None, "auto_pause", "session", session.id)]


def test_game_107_catches_up_on_the_first_request_after_the_start(conn):
    # Nobody asked at the exact second, or the server restarted: the next request still pauses.
    _add(conn)
    assert _tick(conn, AFTER) is True
    assert current_state(conn) == "paused"


def test_game_107_never_pauses_an_off_game(conn):
    _add(conn)
    set_state(conn, "off")
    assert _tick(conn, AT) is False
    assert current_state(conn) == "off"
    # The start time is handled, so Start after it is not overridden.
    set_state(conn, "on")
    assert _tick(conn, AFTER) is False
    assert current_state(conn) == "on"
    assert _audit(conn) == []


def test_game_107_never_resumes_a_paused_game(conn):
    _add(conn)
    set_state(conn, "paused")
    assert _tick(conn, AT) is False
    assert current_state(conn) == "paused"
    assert _audit(conn) == []


def test_game_107_never_repeats_after_a_manual_resume(conn):
    # DEC-049: the session runs late, so an admin resumes by hand. It must stay on.
    _add(conn)
    _tick(conn, AT)
    set_state(conn, "on")
    assert _tick(conn, AFTER) is False
    assert current_state(conn) == "on"
    assert len(_audit(conn)) == 1


def test_game_107_two_sessions_at_once_pause_once(conn):
    _add(conn, title="Example Session 1")
    _add(conn, title="Example Session 2")
    assert _tick(conn, AT) is True
    assert len(_audit(conn)) == 1
    assert (
        conn.execute(
            "SELECT count(*) FROM session WHERE auto_pause_done_at IS NULL"
        ).fetchone()[0]
        == 0
    )


def test_game_107_each_session_pauses_at_its_own_time(conn):
    _add(conn, title="Example Session 1")
    _add(conn, starts_at=TOMORROW, title="Example Session 2")
    _tick(conn, AT)
    set_state(conn, "on")  # the first session ended, game back on
    assert _tick(conn, AFTER) is False
    assert _tick(conn, TOMORROW) is True
    assert current_state(conn) == "paused"


def test_game_107_session_without_a_start_time_never_pauses(conn):
    add(conn, Details("Example Session 1", None, None), FAKE_ADMIN_ID, now=BEFORE)
    assert _tick(conn, TOMORROW) is False
    assert current_state(conn) == "on"


def test_game_107_ended_session_never_pauses(conn):
    session = _add(conn)
    end(conn, session.public_id, FAKE_ADMIN_ID)
    assert _tick(conn, AFTER) is False
    assert current_state(conn) == "on"


def test_game_107_past_start_time_on_save_does_not_pause(conn):
    # An admin adds yesterday's session late: pressing Save must not pause the game.
    _add(conn, now=AFTER)
    assert _tick(conn, AFTER) is False
    assert current_state(conn) == "on"


def test_game_107_moving_start_later_pauses_at_the_new_time(conn):
    session = _add(conn)
    _tick(conn, AT)
    set_state(conn, "on")
    # The session runs late: the admin moves its start, and it pauses again then.
    edit(
        conn,
        session.public_id,
        Details(session.title, LATER_START, 15),
        FAKE_ADMIN_ID,
        now=AFTER,
    )
    assert _tick(conn, AFTER) is False
    assert _tick(conn, LATER_START) is True
    assert current_state(conn) == "paused"


def test_game_107_moving_start_into_the_past_does_not_pause(conn):
    session = _add(conn, starts_at=TOMORROW)
    edit(
        conn,
        session.public_id,
        Details(session.title, START, 15),
        FAKE_ADMIN_ID,
        now=AFTER,
    )
    assert _tick(conn, AFTER) is False
    assert current_state(conn) == "on"


def test_game_107_title_edit_keeps_the_start_time_handled(conn):
    session = _add(conn)
    _tick(conn, AT)
    set_state(conn, "on")
    edit(
        conn,
        session.public_id,
        Details("Example Session 1b", START, 15),
        FAKE_ADMIN_ID,
        now=AFTER,
    )
    assert _tick(conn, AFTER) is False
    assert current_state(conn) == "on"


def test_game_107_flag_off_does_nothing(conn):
    _add(conn)
    assert _tick(conn, AT, enabled=False) is False
    assert current_state(conn) == "on"
    assert conn.execute("SELECT auto_pause_done_at FROM session").fetchone()[0] is None


def test_arch_040_auto_pause_saves_all_or_nothing(conn, monkeypatch):
    _add(conn)

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(sessions.audit, "record", broken_record)
    with pytest.raises(RuntimeError):
        _tick(conn, AT)
    # Nothing saved, so the next request tries again.
    assert current_state(conn) == "on"
    assert conn.execute("SELECT auto_pause_done_at FROM session").fetchone()[0] is None
