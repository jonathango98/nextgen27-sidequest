import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf
from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.db import connect
from app.main import create_app
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


def _post(c, text=None, session="pub-s1", token=True, htmx=True):
    data = {"session": session, "text": words(MIN_WORDS) if text is None else text}
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
