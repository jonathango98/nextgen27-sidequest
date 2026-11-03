import sqlite3

import pytest

from app.config import load_config
from app.db import connect, migrate
from app.services import churches, sessions
from app.services.game_state import current_state, set_state
from app.services.sessions import (
    Details,
    SessionError,
    SessionNotFound,
    add,
    edit,
    end,
    list_all,
    read_details,
    seed_preview,
)

TIMEZONE = load_config()["game"]["timezone"]
FAKE_ADMIN_ID = 7  # fake staff id (ENG-047)
# Fake data only (SAFE-031). Times are made up, in the venue's winter time.
FORM = {
    "title": "Example Session 1",
    "starts_at": "2027-03-06T09:30",
    "checkin_open_minutes": "15",
}


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


def _add(conn, form=FORM):
    add(conn, read_details(form, TIMEZONE), FAKE_ADMIN_ID)
    return list_all(conn)[-1]


def _row(conn, public_id):
    return conn.execute(
        "SELECT * FROM session WHERE public_id = ?", (public_id,)
    ).fetchone()


def _audit(conn):
    return [
        (r["action"], r["target_type"])
        for r in conn.execute("SELECT action, target_type FROM audit_log ORDER BY id")
    ]


def _player(conn):
    churches.load(conn, ["Example Church A"])
    return conn.execute(
        "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18,"
        " pin_hash) VALUES ('testplayer01', 'Test', 'Player 1', 1, 0, 'x')"
    ).lastrowid


# DATA-014: what a session holds.


def test_data_014_session_has_no_room_or_place(conn):
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(session)")}
    assert not columns & {"room", "location", "place", "venue"}  # SAFE-037


def test_data_014_start_time_needs_check_in_minutes(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO session (public_id, title, starts_at)"
            " VALUES ('x', 'Example Session 1', '2027-03-06T15:30:00Z')"
        )


@pytest.mark.parametrize("minutes", [0, -5])
def test_data_014_check_in_minutes_are_above_zero(conn, minutes):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO session (public_id, title, starts_at, checkin_open_minutes)"
            " VALUES ('x', 'Example Session 1', '2027-03-06T15:30:00Z', ?)",
            (minutes,),
        )


def test_data_014_title_cannot_be_blank(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO session (public_id, title) VALUES ('x', '   ')")


def test_data_014_start_time_is_optional(conn):
    session = _add(conn, {"title": "Example Session 1"})
    assert (session.starts_at, session.checkin_open_minutes) == (None, None)


# DATA-022: once per session, and a clean scan order.


def test_data_022_one_check_in_per_player_per_session(conn):
    player_id = _player(conn)
    session = _add(conn)
    conn.execute(
        "INSERT INTO check_in (player_id, session_id, scan_order) VALUES (?, ?, 1)",
        (player_id, session.id),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO check_in (player_id, session_id, scan_order) VALUES (?, ?, 2)",
            (player_id, session.id),
        )


def test_data_022_scan_order_is_unique_in_a_session(conn):
    player_id = _player(conn)
    other_id = conn.execute(
        "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18,"
        " pin_hash) VALUES ('testplayer02', 'Test', 'Player 2', 1, 0, 'x')"
    ).lastrowid
    session = _add(conn)
    conn.execute(
        "INSERT INTO check_in (player_id, session_id, scan_order) VALUES (?, ?, 1)",
        (player_id, session.id),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO check_in (player_id, session_id, scan_order) VALUES (?, ?, 1)",
            (other_id, session.id),
        )


# GAME-021, GAME-105: the form an admin fills in.


def test_game_105_start_time_is_typed_in_venue_time_and_saved_in_utc(conn):
    session = _add(conn)
    # Houston is UTC-6 in March before the clocks change (DATA-004).
    assert session.starts_at == "2027-03-06T15:30:00Z"
    assert sessions.to_local(session.starts_at, TIMEZONE).strftime("%H:%M") == "09:30"


def test_game_021_check_in_minutes_are_saved_with_the_start_time(conn):
    assert _add(conn).checkin_open_minutes == 15


@pytest.mark.parametrize(
    ("form", "message"),
    [
        ({"title": "  "}, "Please give the session a title."),
        ({"title": "x" * (sessions.TITLE_MAX_CHARS + 1)}, "characters"),
        ({"title": "Example Session 1", "starts_at": "soon", "checkin_open_minutes": "5"},
         "Please pick a start date and time."),
        ({"title": "Example Session 1", "starts_at": "2027-03-06T09:30"},
         "how many minutes before the start"),
        ({**FORM, "checkin_open_minutes": "0"}, "whole number above 0"),
        ({**FORM, "checkin_open_minutes": "ten"}, "whole number above 0"),
        ({"title": "Example Session 1", "checkin_open_minutes": "5"},
         "Check-in minutes need a start time too."),
    ],
)  # fmt: skip
def test_game_021_bad_form_is_refused_with_a_message(form, message):
    with pytest.raises(SessionError) as caught:
        read_details(form, TIMEZONE)
    assert message in str(caught.value)


def test_data_014_title_spaces_are_tidied():
    details = read_details({"title": "  Example   Session 1 "}, TIMEZONE)
    assert details.title == "Example Session 1"


def test_data_014_list_is_in_program_order_then_untimed(conn):
    _add(conn, {"title": "Example Session C"})
    _add(conn, {**FORM, "title": "Example Session B", "starts_at": "2027-03-06T13:00"})
    _add(conn, {**FORM, "title": "Example Session A"})
    titles = [s.title for s in list_all(conn)]
    assert titles == ["Example Session A", "Example Session B", "Example Session C"]


# GAME-110, ARCH-050: admins manage sessions, and every change is audited.


def test_arch_050_adding_a_session_writes_an_audit_row(conn):
    session = _add(conn)
    row = conn.execute(
        "SELECT actor_type, actor_id, target_id FROM audit_log"
    ).fetchone()
    assert tuple(row) == ("admin", FAKE_ADMIN_ID, session.id)
    assert _audit(conn) == [("session_add", "session")]


def test_game_110_admin_edits_a_session(conn):
    session = _add(conn)
    new = read_details({"title": "Example Session 1b"}, TIMEZONE)
    assert edit(conn, session.public_id, new, FAKE_ADMIN_ID) is True
    row = _row(conn, session.public_id)
    assert (row["title"], row["starts_at"], row["checkin_open_minutes"]) == (
        "Example Session 1b",
        None,
        None,
    )
    assert _audit(conn)[-1] == ("session_edit", "session")


def test_arch_050_saving_the_same_details_writes_nothing(conn):
    session = _add(conn)
    assert (
        edit(conn, session.public_id, read_details(FORM, TIMEZONE), FAKE_ADMIN_ID)
        is False
    )
    assert _audit(conn) == [("session_add", "session")]


def test_game_110_editing_an_unknown_session_is_refused(conn):
    with pytest.raises(SessionNotFound):
        edit(conn, "nosuchsession", Details("Example", None, None), FAKE_ADMIN_ID)


# GAME-026, OPS-002: End session.


def test_game_026_end_session_resumes_and_opens_takeaways(conn):
    session = _add(conn)
    set_state(conn, "paused")
    result = end(conn, session.public_id, FAKE_ADMIN_ID)
    assert (result.ended, result.resumed) == (True, True)
    assert current_state(conn) == "on"
    assert _row(conn, session.public_id)["ended_at"]  # GAME-036: takeaways open
    assert _audit(conn)[-2:] == [("session_end", "session"), ("game_on", "game_state")]


def test_game_024_end_session_closes_check_in(conn):
    session = _add(conn)
    end(conn, session.public_id, FAKE_ADMIN_ID)
    row = _row(conn, session.public_id)
    assert row["checkin_closed_at"] == row["ended_at"]


def test_game_024_end_session_keeps_an_earlier_check_in_close(conn):
    session = _add(conn)
    conn.execute(
        "UPDATE session SET checkin_closed_at = '2027-03-06T15:30:00Z' WHERE id = ?",
        (session.id,),
    )
    end(conn, session.public_id, FAKE_ADMIN_ID)
    assert _row(conn, session.public_id)["checkin_closed_at"] == "2027-03-06T15:30:00Z"


def test_game_026_end_session_does_not_open_check_in(conn):
    session = _add(conn, {"title": "Example Session 1"})
    end(conn, session.public_id, FAKE_ADMIN_ID)
    assert _row(conn, session.public_id)["checkin_opened_at"] is None


def test_game_026_end_session_while_on_keeps_the_game_on(conn):
    session = _add(conn)
    result = end(conn, session.public_id, FAKE_ADMIN_ID)
    assert (result.ended, result.resumed) == (True, False)
    assert current_state(conn) == "on"
    assert _audit(conn)[-1] == ("session_end", "session")


def test_game_026_end_session_while_off_keeps_the_game_off(conn):
    # Like GAME-107, End session never wakes an off game. Takeaways still open.
    session = _add(conn)
    set_state(conn, "off")
    result = end(conn, session.public_id, FAKE_ADMIN_ID)
    assert (result.ended, result.resumed) == (True, False)
    assert current_state(conn) == "off"
    assert _row(conn, session.public_id)["ended_at"]


def test_game_026_end_session_twice_changes_nothing(conn):
    session = _add(conn)
    set_state(conn, "paused")
    end(conn, session.public_id, FAKE_ADMIN_ID)
    first = _row(conn, session.public_id)["ended_at"]
    audit_rows = _audit(conn)
    # Paused again by hand: a second press must not resume it.
    set_state(conn, "paused")
    result = end(conn, session.public_id, FAKE_ADMIN_ID)
    assert (result.ended, result.resumed) == (False, False)
    assert current_state(conn) == "paused"
    assert _row(conn, session.public_id)["ended_at"] == first
    assert _audit(conn) == audit_rows


def test_game_026_ending_an_unknown_session_is_refused(conn):
    set_state(conn, "paused")
    with pytest.raises(SessionNotFound):
        end(conn, "nosuchsession", FAKE_ADMIN_ID)
    assert current_state(conn) == "paused"


def test_arch_040_end_session_saves_all_or_nothing(conn, monkeypatch):
    session = _add(conn)
    set_state(conn, "paused")

    def broken_change(*args, **kwargs):
        raise RuntimeError("game state write failed")

    monkeypatch.setattr(sessions.game_state, "change_in_transaction", broken_change)
    with pytest.raises(RuntimeError):
        end(conn, session.public_id, FAKE_ADMIN_ID)
    # The resume failed, so the session is not ended and no audit row stays.
    assert _row(conn, session.public_id)["ended_at"] is None
    assert current_state(conn) == "paused"
    assert _audit(conn) == [("session_add", "session")]


# ENG-113: the PR preview seed.


def test_eng_113_preview_seed_adds_one_fake_session_once(conn):
    assert seed_preview(conn) == [sessions.PREVIEW_SESSION]
    assert seed_preview(conn) == []
    assert [s.title for s in list_all(conn)] == [sessions.PREVIEW_SESSION]
