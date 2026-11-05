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
        "visibility": "private",
        "review_scope": CFG["journal"]["review_scope"],
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


# journal.share-review: who can read a note, and the admin review (GAME-031, SAFE-007, DEC-076).

SCOPE = CFG["journal"]["review_scope"]


@pytest.fixture
def admin(conn):
    return conn.execute(
        "INSERT INTO staff_account (username, password_hash, role)"
        " VALUES ('test-admin-1', 'not-a-real-hash', 'admin')"
    ).lastrowid


def share(conn, player, visibility, text=None, session="pub-s1"):
    submit(conn, player, session, text=text, visibility=visibility)
    return journal.list_own(conn, player)[0].public_id


def change(conn, player, public_id, visibility):
    journal.change_visibility(
        conn,
        player_id=player,
        takeaway_public_id=public_id,
        visibility=visibility,
        review_scope=SCOPE,
    )


def status(conn, public_id):
    return tuple(
        conn.execute(
            "SELECT visibility, review_status FROM takeaway WHERE public_id = ?",
            (public_id,),
        ).fetchone()
    )


def audit_actions(conn):
    return [r[0] for r in conn.execute("SELECT action FROM audit_log ORDER BY id")]


def test_data_003_takeaways_get_a_random_public_id(conn, players):
    add_session(conn, 1)
    first = share(conn, players[0], "private")
    second = share(conn, players[0], "private")
    assert first != second
    assert not first.isdigit() and len(first) >= 12


@pytest.mark.parametrize("visibility", journal.VISIBILITIES)
def test_game_031_same_points_for_every_choice(conn, players, visibility):
    add_session(conn, 1)
    assert submit(conn, players[0], visibility=visibility).points == AMOUNT
    assert score(conn, players[0]) == AMOUNT


def test_safe_007_a_shared_note_waits_for_review(conn, players):
    add_session(conn, 1)
    named = share(conn, players[0], "shared_named")
    anon = share(conn, players[0], "shared_anonymous")
    assert status(conn, named) == ("shared_named", "pending")
    assert status(conn, anon) == ("shared_anonymous", "pending")
    assert journal.list_approved(conn) == []


def test_game_031_a_made_up_choice_is_refused(conn, players):
    add_session(conn, 1)
    with pytest.raises(journal.TakeawayRefused) as refused:
        submit(conn, players[0], visibility="everyone")
    assert refused.value.code == "BAD_INPUT"
    assert _count(conn, "takeaway") == 0


def test_safe_008_only_the_stricter_scope_is_known(conn, players):
    add_session(conn, 1)
    assert SCOPE == "all_shared"
    with pytest.raises(ValueError):
        submit(
            conn, players[0], visibility="shared_named", review_scope="something_else"
        )


def test_safe_040_approve_shows_it_and_writes_an_audit_row(conn, players, admin):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_named")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    assert status(conn, note) == ("shared_named", "approved")
    assert [n.text for n in journal.list_approved(conn)] == [words(MIN_WORDS)]
    row = conn.execute(
        "SELECT actor_type, actor_id, action, target_type FROM audit_log"
        " WHERE action = 'review_approve'"
    ).fetchone()
    assert tuple(row) == ("admin", admin, "review_approve", "takeaway")


def test_safe_040_reject_keeps_it_hidden_and_keeps_the_points(conn, players, admin):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_named")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="reject")
    assert status(conn, note) == ("shared_named", "rejected")
    assert journal.list_approved(conn) == []
    assert score(conn, players[0]) == AMOUNT
    assert "review_reject" in audit_actions(conn)


def test_safe_041_hide_an_approved_note_with_an_audit_row(conn, players, admin):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_anonymous")
    with pytest.raises(journal.TakeawayRefused):  # only an approved note can be hidden
        journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="hide")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="hide")
    assert status(conn, note) == ("shared_anonymous", "hidden")
    assert journal.list_approved(conn) == []
    assert audit_actions(conn)[-1] == "review_hide"


@pytest.mark.parametrize("undo", ["reject", "hide"])
def test_dec_076_admin_can_approve_again_after_reject_or_hide(
    conn, players, admin, undo
):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_named")
    if undo == "hide":
        journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome=undo)
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    assert status(conn, note) == ("shared_named", "approved")


def test_safe_040_a_second_review_of_the_same_note_is_refused(conn, players, admin):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_named")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    with pytest.raises(journal.TakeawayRefused) as refused:
        journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="reject")
    assert refused.value.code == "ALREADY_DONE"
    assert status(conn, note) == ("shared_named", "approved")


def test_safe_029_private_notes_are_never_in_the_review_queue(conn, players, admin):
    add_session(conn, 1)
    private = share(conn, players[0], "private")
    share(conn, players[1], "shared_named")
    queue = journal.review_queue(conn, "pending")
    assert len(queue) == 1 and queue[0].public_id != private
    with pytest.raises(journal.TakeawayRefused) as refused:
        journal.review(
            conn, admin_id=admin, takeaway_public_id=private, outcome="approve"
        )
    assert refused.value.code == "NOT_FOUND"
    assert status(conn, private) == ("private", "not_needed")


def test_safe_009_admins_see_who_wrote_an_anonymous_note(conn, players):
    add_session(conn, 1)
    share(conn, players[1], "shared_anonymous")
    [note] = journal.review_queue(conn, "pending")
    assert (note.first_name, note.last_name, note.church) == (
        "Test",
        "Player 2",
        "Example Church A",
    )


def test_safe_009_players_never_get_the_author_of_an_anonymous_note(
    conn, players, admin
):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_anonymous")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    [shared] = journal.list_approved(conn)
    assert (shared.first_name, shared.church) == (None, None)


def test_ui_038_summary_is_newest_session_first_with_first_name_and_church(
    conn, players, admin
):
    add_session(conn, 1)
    add_session(conn, 2)
    for session, word in (("pub-s1", "early"), ("pub-s2", "late")):
        note = share(conn, players[0], "shared_named", words(MIN_WORDS, word), session)
        journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    shared = journal.list_approved(conn)
    assert [(n.session_title, n.text.split()[0]) for n in shared] == [
        ("Example Session 2", "late"),
        ("Example Session 1", "early"),
    ]
    # SAFE-028: first name and church only, never the last name.
    assert vars(shared[0]).keys() == {"session_title", "text", "first_name", "church"}
    assert (shared[0].first_name, shared[0].church) == ("Test", "Example Church A")


def test_dec_076_sharing_a_private_note_sends_it_for_review(conn, players):
    add_session(conn, 1)
    note = share(conn, players[0], "private")
    change(conn, players[0], note, "shared_named")
    assert status(conn, note) == ("shared_named", "pending")
    assert audit_actions(conn)[-1] == "visibility_shared_named"


def test_dec_076_named_to_anonymous_keeps_the_approval(conn, players, admin):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_named")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    change(conn, players[0], note, "shared_anonymous")
    assert status(conn, note) == ("shared_anonymous", "approved")
    change(conn, players[0], note, "shared_named")
    assert status(conn, note) == ("shared_named", "approved")


def test_dec_076_making_an_approved_note_private_then_sharing_reviews_again(
    conn, players, admin
):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_named")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    change(conn, players[0], note, "private")
    assert status(conn, note) == ("private", "not_needed")
    assert journal.list_approved(conn) == []
    change(conn, players[0], note, "shared_named")
    assert status(conn, note) == ("shared_named", "pending")


@pytest.mark.parametrize("outcome", ["reject", "hide"])
def test_dec_076_a_turned_down_note_can_only_go_private(conn, players, admin, outcome):
    add_session(conn, 1)
    note = share(conn, players[0], "shared_named")
    if outcome == "hide":
        journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome=outcome)
    with pytest.raises(journal.TakeawayRefused):
        change(conn, players[0], note, "shared_anonymous")
    change(conn, players[0], note, "private")
    locked = "rejected" if outcome == "reject" else "hidden"
    assert status(conn, note) == ("private", locked)
    assert journal.list_own(conn, players[0])[0].can_share is False
    for visibility in journal.SHARED:
        with pytest.raises(journal.TakeawayRefused):
            change(conn, players[0], note, visibility)
    assert status(conn, note) == ("private", locked)


def test_dec_076_a_turned_down_note_cannot_be_shared_in_the_database(conn, players):
    session = add_session(conn, 1)
    for bad in [
        ("shared_named", "not_needed"),
        ("private", "pending"),
        ("private", "approved"),
    ]:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO takeaway (player_id, session_id, text, visibility, review_status)"
                " VALUES (?, ?, 'Example takeaway', ?, ?)",
                (players[0], session, *bad),
            )


def test_dec_076_players_change_only_their_own_notes(conn, players):
    add_session(conn, 1)
    note = share(conn, players[0], "private")
    with pytest.raises(journal.TakeawayRefused) as refused:
        change(conn, players[1], note, "shared_named")
    assert refused.value.code == "NOT_FOUND"
    assert status(conn, note) == ("private", "not_needed")


@pytest.mark.parametrize("state", ["paused", "off"])
def test_dec_076_changing_who_can_read_is_blocked_while_paused_or_off(
    conn, players, state
):
    add_session(conn, 1)
    note = share(conn, players[0], "private")
    set_state(conn, state)
    with pytest.raises(GameNotOn):
        change(conn, players[0], note, "shared_named")
    assert status(conn, note) == ("private", "not_needed")


def test_dec_076_choosing_the_same_option_writes_nothing(conn, players):
    add_session(conn, 1)
    note = share(conn, players[0], "private")
    before = audit_actions(conn)
    change(conn, players[0], note, "private")
    assert audit_actions(conn) == before
