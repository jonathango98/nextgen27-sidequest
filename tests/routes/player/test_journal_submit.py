import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf
from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.services import journal
from app.services.game_state import set_state
from tests.conftest import seed_fake_players

FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=0)  # fake data (ENG-047)
# Real numbers from config, never a hardcoded game number (AI-013).
CFG = load_config()
AMOUNT = CFG["points"]["journal_takeaway"]
MIN_WORDS = CFG["limits"]["journal_min_words"]


def words(n: int, word: str = "listen") -> str:
    return " ".join([word] * n)


@pytest.fixture
def db(tmp_path):
    app = create_app()
    db_path = tmp_path / "journal.db"
    seed_fake_players(db_path, FAKE_PLAYER.public_id, "testpid02")
    conn = connect(db_path)
    conn.execute(
        "INSERT INTO session (public_id, title, ended_at) VALUES"
        " ('pub-s1', 'Example Session 1', '2027-03-05T10:00:00Z'),"
        " ('pub-s2', 'Example Session 2', NULL)"
    )
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    with TestClient(app, base_url="https://testserver") as c:
        # Starting sets db_path from SQ_DB_PATH, so point it back at this test's database.
        app.state.db_path = db_path
        c.get("/journal/new")  # sets the CSRF cookie
        yield c, conn
    conn.close()


def _post(c, text=None, session="pub-s1", token=True, htmx=True, visibility="private"):
    data = {
        "session": session,
        "text": words(MIN_WORDS) if text is None else text,
        "visibility": visibility,
    }
    if token:
        data["csrf_token"] = c.cookies.get(csrf.COOKIE)
    headers = {"HX-Request": "true"} if htmx else {}
    return c.post("/journal", data=data, headers=headers, follow_redirects=False)


def _as(c, public_id):
    c.app.dependency_overrides[get_current_player] = lambda: CurrentPlayer(public_id, 0)


def _count(conn):
    return conn.execute("SELECT count(*) FROM takeaway").fetchone()[0]


def test_arch_038_journal_needs_csrf_token(db):
    c, conn = db
    assert _post(c, token=False).status_code == 400
    assert _count(conn) == 0


def test_game_036_form_offers_only_ended_sessions(db):
    c, _ = db
    html = c.get("/journal/new").text
    assert 'value="pub-s1"' in html
    assert "pub-s2" not in html
    assert f"0 / {MIN_WORDS} words" in html  # GAME-030: minimum from config


def test_game_036_no_ended_session_shows_a_friendly_note(db):
    c, conn = db
    conn.execute("UPDATE session SET ended_at = NULL")
    html = c.get("/journal/new").text
    assert "Takeaways open when a session ends." in html
    assert "<textarea" not in html


def test_game_030_submit_saves_and_goes_to_journal_with_points(db):
    c, _ = db
    response = _post(c)
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/journal?saved=points"
    html = c.get("/journal?saved=points").text
    assert f'Saved! <span class="pill">+{AMOUNT}</span>' in html
    assert words(MIN_WORDS) in html


def test_game_030_second_note_same_session_saves_with_no_points(db):
    # DEC-072
    c, conn = db
    _post(c)
    response = _post(c, words(MIN_WORDS, "pray"))
    assert response.headers["hx-redirect"] == "/journal?saved=extra"
    assert _count(conn) == 2
    html = c.get("/journal/new").text
    # The paid session is still offered, with no points pill on Submit.
    assert 'data-paid="1"' in html
    assert "data-submit-pill hidden" in html


def test_game_030_short_note_keeps_the_text_and_says_how_many_more(db):
    c, conn = db
    response = _post(c, words(MIN_WORDS - 2))
    assert response.status_code == 400
    assert 'data-error-code="TOO_SHORT"' in response.text
    assert "Add 2 more words to save this." in response.text
    assert words(MIN_WORDS - 2) in response.text  # kept, so nothing is lost
    assert "<html" not in response.text  # API-002: only the form
    assert _count(conn) == 0


def test_game_036_note_for_a_session_not_ended_is_not_found(db):
    c, conn = db
    response = _post(c, session="pub-s2")
    assert response.status_code == 404
    assert 'data-error-code="NOT_FOUND"' in response.text
    assert _count(conn) == 0


@pytest.mark.parametrize(("state", "code"), [("paused", "PAUSED"), ("off", "GAME_OFF")])
def test_game_033_no_note_while_paused_or_off(db, state, code):
    c, conn = db
    set_state(conn, state)
    response = _post(c)
    assert response.status_code == 423
    assert f'data-error-code="{code}"' in response.text
    assert words(MIN_WORDS) in response.text  # kept for later
    assert _count(conn) == 0


def test_game_031_each_player_lists_only_their_own_notes(db):
    c, _ = db
    _post(c, words(MIN_WORDS, "mine"))
    _as(c, "testpid02")
    _post(c, words(MIN_WORDS, "theirs"))
    html = c.get("/journal").text
    assert words(MIN_WORDS, "theirs") in html
    assert words(MIN_WORDS, "mine") not in html


def test_game_030_without_htmx_submit_redirects(db):
    c, _ = db
    response = _post(c, htmx=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/journal?saved=points"


def test_game_030_made_up_saved_value_shows_nothing(db):
    c, _ = db
    html = c.get("/journal?saved=1000").text
    assert "Saved" not in html


def test_game_031_empty_journal_says_so(db):
    c, _ = db
    assert "No notes yet." in c.get("/journal").text


def test_game_031_notes_are_listed_by_session_as_just_me(db):
    c, conn = db
    conn.execute(
        "INSERT INTO session (public_id, title, ended_at)"
        " VALUES ('pub-s3', 'Example Session 3', '2027-03-05T12:00:00Z')"
    )
    _post(c, words(MIN_WORDS, "first"))
    _post(c, words(MIN_WORDS, "second"), session="pub-s3")
    _post(c, words(MIN_WORDS, "third"), session="pub-s3")
    html = c.get("/journal").text
    sessions = re.findall(r'<h2 class="session-title"[^>]*>([^<]+)</h2>', html)
    assert sessions == ["Example Session 3", "Example Session 1"]
    texts = re.findall(r'<p class="takeaway-text">(\w+)', html)
    assert texts == ["third", "second", "first"]
    assert html.count('<span class="note-status">Just me</span>') == 3


def test_game_031_each_note_shows_who_can_read_it(db):
    c, _ = db
    for visibility in ("shared_anonymous", "shared_named", "private"):
        _post(c, visibility=visibility)
    html = c.get("/journal").text
    labels = re.findall(r'<span class="note-status">([^<]+)</span>', html)
    assert labels == ["Just me", "Shared with my name", "Shared anonymously"]
    # DEC-076: the player sees only their choice, never "waiting for review".
    assert "review" not in html.lower()


def test_game_031_a_missing_choice_saves_nothing(db):
    c, conn = db
    response = _post(c, visibility="")
    assert response.status_code == 400
    assert "Please choose who can read this." in response.text
    assert _count(conn) == 0


# DEC-076: change who can read a note from the Journal list.


def _note(conn):
    return conn.execute(
        "SELECT public_id, visibility, review_status FROM takeaway ORDER BY id DESC"
    ).fetchone()


def _change(c, public_id, visibility, token=True, htmx=True):
    data = {"visibility": visibility}
    if token:
        data["csrf_token"] = c.cookies.get(csrf.COOKIE)
    headers = {"HX-Request": "true"} if htmx else {}
    return c.post(
        f"/journal/{public_id}/visibility",
        data=data,
        headers=headers,
        follow_redirects=False,
    )


def test_dec_076_change_who_can_read_from_the_journal_list(db):
    c, conn = db
    _post(c)
    note = _note(conn)["public_id"]
    assert f'action="/journal/{note}/visibility"' in c.get("/journal").text
    response = _change(c, note, "shared_anonymous")
    assert response.status_code == 200
    assert f'id="note-{note}"' in response.text
    assert '<span class="note-status">Shared anonymously</span>' in response.text
    assert 'role="status">Saved.' in response.text
    assert tuple(_note(conn))[1:] == ("shared_anonymous", "pending")


def test_dec_076_without_htmx_it_goes_back_to_the_journal(db):
    c, conn = db
    _post(c)
    response = _change(c, _note(conn)["public_id"], "shared_named", htmx=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/journal"
    assert _note(conn)["visibility"] == "shared_named"


@pytest.mark.parametrize("htmx", [True, False])
def test_dec_076_someone_elses_note_is_not_found(db, htmx):
    c, conn = db
    _post(c)
    note = _note(conn)["public_id"]
    _as(c, "testpid02")
    response = _change(c, note, "shared_named", htmx=htmx)
    assert response.status_code == 404
    assert "find that." in response.text
    assert _note(conn)["visibility"] == "private"


def test_dec_076_a_change_needs_the_csrf_token(db):
    c, conn = db
    _post(c)
    response = _change(c, _note(conn)["public_id"], "shared_named", token=False)
    assert response.status_code == 400
    assert _note(conn)["visibility"] == "private"


@pytest.mark.parametrize("state", ["paused", "off"])
def test_dec_076_a_change_is_refused_while_paused_or_off(db, state):
    c, conn = db
    _post(c)
    note = _note(conn)["public_id"]
    set_state(conn, state)
    response = _change(c, note, "shared_named")
    assert response.status_code == 423
    assert 'role="alert"' in response.text and f'id="note-{note}"' in response.text
    assert _note(conn)["visibility"] == "private"


def test_dec_076_a_turned_down_note_offers_only_just_me(db):
    c, conn = db
    _post(c, visibility="shared_named")
    note = _note(conn)["public_id"]
    admin = conn.execute(
        "INSERT INTO staff_account (username, password_hash, role)"
        " VALUES ('test-admin-1', 'not-a-real-hash', 'admin')"
    ).lastrowid
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="reject")
    card = c.get("/journal").text
    assert re.findall(r'name="visibility" value="(\w+)"', card) == ["private"]
    response = _change(c, note, "shared_anonymous")
    assert response.status_code == 400
    assert "This note can only be kept private." in response.text
    assert tuple(_note(conn))[1:] == ("shared_named", "rejected")


# The Summary page: approved shared notes only (SAFE-007, SAFE-017, UI-038).


def _admin(conn):
    row = conn.execute(
        "SELECT id FROM staff_account WHERE username = 'test-admin-1'"
    ).fetchone()
    if row:
        return row[0]
    return conn.execute(
        "INSERT INTO staff_account (username, password_hash, role)"
        " VALUES ('test-admin-1', 'not-a-real-hash', 'admin')"
    ).lastrowid


def _authors(html):
    return re.findall(r'<p class="takeaway-author">([^<]+)</p>', html)


def test_safe_007_summary_shows_only_approved_shared_notes(db):
    c, conn = db
    for word, visibility in (
        ("named", "shared_named"),
        ("anon", "shared_anonymous"),
        ("waiting", "shared_named"),
        ("private", "private"),
    ):
        _post(c, words(MIN_WORDS, word), visibility=visibility)
    assert "No shared takeaways yet." in c.get("/summary").text
    rows = conn.execute("SELECT public_id, text FROM takeaway").fetchall()
    ids = {r["text"].split()[0]: r["public_id"] for r in rows}
    for word in ("named", "anon"):
        journal.review(
            conn, admin_id=_admin(conn), takeaway_public_id=ids[word], outcome="approve"
        )
    _as(c, "testpid02")  # another signed-in player
    html = c.get("/summary").text
    texts = re.findall(r'<p class="takeaway-text">(\w+)', html)
    assert texts == ["anon", "named"]  # newest first within the session
    assert "waiting" not in html and "private" not in html


def test_safe_009_summary_shows_anonymous_without_a_name(db):
    c, conn = db
    _post(c, words(MIN_WORDS, "anon"), visibility="shared_anonymous")
    _post(c, words(MIN_WORDS, "named"), visibility="shared_named")
    for (note,) in conn.execute("SELECT public_id FROM takeaway").fetchall():
        journal.review(
            conn, admin_id=_admin(conn), takeaway_public_id=note, outcome="approve"
        )
    html = c.get("/summary").text
    assert _authors(html) == ["Test · Example Church A", "Anonymous"]
    assert "Player 1" not in html  # SAFE-028: never the last name


def test_ui_038_summary_is_grouped_newest_session_first(db):
    c, conn = db
    conn.execute(
        "INSERT INTO session (public_id, title, ended_at)"
        " VALUES ('pub-s3', 'Example Session 3', '2027-03-05T12:00:00Z')"
    )
    _post(c, words(MIN_WORDS, "early"), visibility="shared_named")
    _post(c, words(MIN_WORDS, "late"), session="pub-s3", visibility="shared_named")
    for (note,) in conn.execute("SELECT public_id FROM takeaway").fetchall():
        journal.review(
            conn, admin_id=_admin(conn), takeaway_public_id=note, outcome="approve"
        )
    html = c.get("/summary").text
    titles = re.findall(r'<h2 class="session-title"[^>]*>([^<]+)</h2>', html)
    assert titles == ["Example Session 3", "Example Session 1"]


def test_safe_041_a_hidden_note_leaves_the_summary(db):
    c, conn = db
    _post(c, words(MIN_WORDS, "named"), visibility="shared_named")
    note = _note(conn)["public_id"]
    admin = _admin(conn)
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="approve")
    assert "named" in c.get("/summary").text
    journal.review(conn, admin_id=admin, takeaway_public_id=note, outcome="hide")
    assert "No shared takeaways yet." in c.get("/summary").text
