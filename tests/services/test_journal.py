import sqlite3

import pytest

from app.config import load_config
from app.db import connect, migrate
from app.services import journal
from app.services.game_state import GameNotOn, set_state
from app.services.points import score

FAKE_PIN_HASH = "not-a-real-hash"  # fake data (ENG-047)
# Real numbers from config, never a hardcoded game number (AI-013).
CFG = load_config()
AMOUNT = CFG["points"]["journal_takeaway"]
MIN_WORDS = CFG["limits"]["journal_min_words"]


def words(n: int, word: str = "listen") -> str:
    return " ".join([word] * n)


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def players(conn):
    church = conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church A')"
    ).lastrowid
    return [
        conn.execute(
            "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " VALUES (?, 'Test', ?, ?, 0, ?)",
            (f"pub-{n}", f"Player {n}", church, FAKE_PIN_HASH),
        ).lastrowid
        for n in (1, 2)
    ]


def add_session(conn, n: int, *, ended: bool = True) -> int:
    return conn.execute(
        "INSERT INTO session (public_id, title, ended_at) VALUES (?, ?, ?)",
        (
            f"pub-s{n}",
            f"Example Session {n}",
            f"2027-03-05T1{n}:00:00Z" if ended else None,
        ),
    ).lastrowid


def submit(conn, player, session_public_id="pub-s1", text=None, **overrides):
    args = {
        "player_id": player,
        "session_public_id": session_public_id,
        "text": words(MIN_WORDS) if text is None else text,
        "min_words": MIN_WORDS,
        "amount": AMOUNT,
        "require_checkin": False,
    }
    return journal.submit(conn, **{**args, **overrides})


def _count(conn, table):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_game_034_god_is_good_is_three_words():
    assert journal.count_words("God is good") == 3


def test_game_034_line_breaks_split_and_punctuation_alone_is_not_a_word():
    assert journal.count_words("God is good\n-\nall the time !!") == 6
    assert journal.count_words("  \n - ... ") == 0


def test_game_030_short_note_says_how_many_more_words_and_saves_nothing(conn, players):
    # Worked example E6: one word short is refused, with nothing saved.
    add_session(conn, 1)
    with pytest.raises(journal.TakeawayRefused) as refused:
        submit(conn, players[0], text=words(MIN_WORDS - 1))
    assert (refused.value.status, refused.value.code) == (400, "TOO_SHORT")
    assert refused.value.message == "Add 1 more word to save this."
    assert _count(conn, "takeaway") == 0
    assert score(conn, players[0]) == 0


def test_game_030_punctuation_does_not_pad_a_short_note(conn, players):
    add_session(conn, 1)
    with pytest.raises(journal.TakeawayRefused) as refused:
        submit(conn, players[0], text=words(MIN_WORDS - 3) + " - - - ! ?")
    assert refused.value.message == "Add 3 more words to save this."


def test_game_030_first_note_for_a_session_pays_the_config_points(conn, players):
    add_session(conn, 1)
    saved = submit(conn, players[0])
    assert saved.points == AMOUNT
    assert score(conn, players[0]) == AMOUNT


def test_game_030_second_note_same_session_saves_with_no_points(conn, players):
    # DEC-072: many notes per session, points for the first one only.
    add_session(conn, 1)
    submit(conn, players[0])
    saved = submit(conn, players[0], text=words(MIN_WORDS, "pray"))
    assert saved.points == 0
    assert _count(conn, "takeaway") == 2
    assert score(conn, players[0]) == AMOUNT


def test_game_030_each_session_pays_once(conn, players):
    add_session(conn, 1)
    add_session(conn, 2)
    submit(conn, players[0], "pub-s1")
    assert submit(conn, players[0], "pub-s2").points == AMOUNT
    assert score(conn, players[0]) == 2 * AMOUNT


def test_game_030_a_second_note_still_needs_enough_words(conn, players):
    add_session(conn, 1)
    submit(conn, players[0])
    with pytest.raises(journal.TakeawayRefused):
        submit(conn, players[0], text=words(MIN_WORDS - 1))
    assert _count(conn, "takeaway") == 1


@pytest.mark.parametrize("state", ["paused", "off"])
def test_game_033_no_note_while_paused_or_off(conn, players, state):
    add_session(conn, 1)
    set_state(conn, state)
    with pytest.raises(GameNotOn):
        submit(conn, players[0])
    assert _count(conn, "takeaway") == 0
    assert score(conn, players[0]) == 0


def test_game_036_only_ended_sessions_take_notes(conn, players):
    add_session(conn, 1, ended=False)
    with pytest.raises(journal.TakeawayRefused) as refused:
        submit(conn, players[0])
    assert (refused.value.status, refused.value.code) == (404, "NOT_FOUND")
    assert journal.sessions_to_write(conn, players[0], require_checkin=False) == []


def test_game_036_unknown_session_is_not_found(conn, players):
    with pytest.raises(journal.TakeawayRefused) as refused:
        submit(conn, players[0], "pub-nope")
    assert refused.value.code == "NOT_FOUND"


def test_game_036_sessions_to_write_newest_first_and_marks_paid(conn, players):
    add_session(conn, 1)
    add_session(conn, 2)
    add_session(conn, 3, ended=False)
    submit(conn, players[0], "pub-s1")
    choices = journal.sessions_to_write(conn, players[0], require_checkin=False)
    assert [(c.title, c.paid) for c in choices] == [
        ("Example Session 2", False),
        ("Example Session 1", True),  # still offered: more notes are allowed (DEC-072)
    ]


def test_game_035_check_in_needed_only_when_config_says(conn, players):
    session = add_session(conn, 1)
    assert CFG["journal"]["require_checkin"] is False
    assert journal.sessions_to_write(conn, players[0], require_checkin=True) == []
    with pytest.raises(journal.TakeawayRefused):
        submit(conn, players[0], require_checkin=True)
    conn.execute(
        "INSERT INTO check_in (player_id, session_id, scan_order) VALUES (?, ?, 1)",
        (players[0], session),
    )
    assert submit(conn, players[0], require_checkin=True).points == AMOUNT


def test_game_031_new_notes_are_private_and_need_no_review(conn, players):
    add_session(conn, 1)
    submit(conn, players[0])
    row = conn.execute("SELECT visibility, review_status FROM takeaway").fetchone()
    assert tuple(row) == ("private", "not_needed")


def test_safe_007_a_shared_note_cannot_skip_review(conn, players):
    session = add_session(conn, 1)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO takeaway (player_id, session_id, text, visibility)"
            " VALUES (?, ?, 'Example takeaway', 'shared_named')",
            (players[0], session),
        )


def test_game_031_players_list_only_their_own_notes(conn, players):
    add_session(conn, 1)
    add_session(conn, 2)
    submit(conn, players[0], "pub-s1", text=words(MIN_WORDS, "first"))
    submit(conn, players[0], "pub-s2", text=words(MIN_WORDS, "second"))
    submit(conn, players[0], "pub-s2", text=words(MIN_WORDS, "third"))
    submit(conn, players[1], "pub-s1", text=words(MIN_WORDS, "other"))
    own = journal.list_own(conn, players[0])
    assert [(n.session_title, n.text.split()[0]) for n in own] == [
        ("Example Session 2", "third"),
        ("Example Session 2", "second"),
        ("Example Session 1", "first"),
    ]
    assert [n.text.split()[0] for n in journal.list_own(conn, players[1])] == ["other"]
