import re

import pytest
from fastapi.testclient import TestClient

from app.auth.current import CurrentPlayer, get_current_player
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.routes.player import join
from app.services import qr
from app.services.game_state import BANNERS, set_state
from tests.conftest import seed_fake_players

FAKE_PLAYER = CurrentPlayer(public_id="testpid01", score=120)  # fake data (ENG-047)
FAKE_QR_KEY = "test-only-fake-signing-key"  # never a real key (SAFE-030)
# Player pages with the bottom bar, which all share player/base.html (UI-030). Wrapped has its own
# full-screen frame and no note, since it is the main thing to do once the game is off (GAME-108).
PAGES = (
    "/",
    "/code",
    "/quests",
    "/scan",
    "/connections/1",
    "/journal",
    "/journal/new",
    "/summary",
    "/box",
)


def disabled_button(label):
    # A switched-off button whose text includes label, allowing icons and pills around it.
    return re.compile(
        r'<button class="[^"]*" type="button" disabled>(?:(?!</button>).)*?\b'
        + re.escape(label)
        + r"\b",
        re.DOTALL,
    )


def page_text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Own database per test, so a state change never leaks into other tests.
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "side-quest.db"))
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    app = create_app()
    app.dependency_overrides[get_current_player] = lambda: FAKE_PLAYER
    with TestClient(app, base_url="https://testserver") as c:
        # My Code and the icebreaker read the player's rows, and /connections/1 is their pair.
        ids = seed_fake_players(c.app.state.db_path, FAKE_PLAYER.public_id, "testpid02")
        conn = connect(c.app.state.db_path)
        conn.execute(
            "INSERT INTO connection (id, player_low_id, player_high_id, scanner_id,"
            " question_category, is_same_church) VALUES (1, ?, ?, ?, 'food', 1)",
            (*sorted(ids.values()), ids[FAKE_PLAYER.public_id]),
        )
        conn.close()
        yield c


def _set(client, state):
    conn = connect(client.app.state.db_path)
    try:
        set_state(conn, state)
    finally:
        conn.close()


def _banner(text):
    return f'<p class="game-banner" role="status">{text}</p>'


@pytest.mark.parametrize("path", PAGES)
def test_ui_033_paused_note_on_every_player_page(client, path):
    _set(client, "paused")
    response = client.get(path)
    assert response.status_code == 200
    assert _banner(BANNERS["paused"]) in response.text


@pytest.mark.parametrize("path", PAGES)
def test_game_108_closed_note_while_off(client, path):
    _set(client, "off")
    assert _banner(BANNERS["off"]) in client.get(path).text


@pytest.mark.parametrize("path", PAGES)
def test_ui_033_no_note_while_on(client, path):
    assert "game-banner" not in client.get(path).text


def test_arch_042_note_goes_away_on_the_next_page_after_start(client):
    _set(client, "paused")
    assert "game-banner" in client.get("/").text
    _set(client, "on")
    assert "game-banner" not in client.get("/").text


def test_game_108_join_page_says_closed_while_off(client):
    _set(client, "off")
    response = client.get("/join")
    assert response.status_code == 200
    assert join.CLOSED in response.text
    assert 'name="first_name"' not in response.text
    assert 'href="/login"' in response.text


def test_game_102_join_page_stays_open_while_paused(client):
    _set(client, "paused")
    response = client.get("/join")
    assert join.CLOSED not in response.text
    assert 'name="first_name"' in response.text


def test_game_108_login_page_still_works_while_off(client):
    _set(client, "off")
    response = client.get("/login")
    assert response.status_code == 200
    assert 'name="pin"' in response.text


@pytest.mark.parametrize(
    ("state", "paused_look"), [("on", False), ("paused", True), ("off", False)]
)
def test_ui_033_paused_look_only_while_paused(client, state, paused_look):
    _set(client, state)
    assert ('<body class="paused">' in client.get("/").text) is paused_look


@pytest.mark.parametrize("state", ["paused", "off"])
def test_game_102_home_play_buttons_wait_while_not_on(client, state):
    _set(client, state)
    html = client.get("/").text
    assert 'href="/scan"' not in html
    assert disabled_button("Meet friends").search(html)


def test_dec_066_home_stays_open_while_paused_with_reading_greyed_out(client):
    _set(client, "paused")
    html = client.get("/").text
    assert "120 points" in page_text(html)  # FAKE_PLAYER's score
    assert "Back after the session." not in html
    assert 'href="/summary"' not in html
    assert 'href="/box"' not in html
    assert disabled_button("Read").search(html)
    assert disabled_button("Write").search(html)


def test_game_108_reading_stays_open_while_off(client):
    _set(client, "off")
    html = client.get("/").text
    assert 'href="/summary"' in html
    assert 'href="/box"' in html


def test_game_102_home_play_buttons_work_while_on(client):
    html = client.get("/").text
    assert 'href="/scan"' in html
    assert 'href="/journal"' in html


@pytest.mark.parametrize("path", [p for p in PAGES if p != "/"])
def test_dec_066_every_other_page_shows_the_paused_screen(client, path):
    _set(client, "paused")
    html = client.get(path).text
    assert "Back after the session." in html
    assert 'class="qr-panel"' not in html
    assert "data-scanner" not in html


@pytest.mark.parametrize("path", [p for p in PAGES if p != "/"])
def test_dec_066_pages_open_again_after_start(client, path):
    _set(client, "paused")
    client.get(path)
    _set(client, "on")
    assert "Back after the session." not in client.get(path).text


def test_dec_066_open_my_code_page_loses_its_code_while_paused(client):
    _set(client, "paused")
    response = client.get("/code/qr", headers={"HX-Request": "true"})
    assert response.status_code == 423
    assert 'data-error-code="PAUSED"' in response.text
    assert "<svg" not in response.text


def test_game_108_my_code_still_shows_while_off_but_scan_waits(client):
    _set(client, "off")
    html = client.get("/code").text
    assert 'class="qr-panel"' in html  # blind box claims on Sunday need it (GAME-078)
    assert 'href="/scan"' not in html
    assert disabled_button("Scan").search(html)
    assert client.get("/code/qr").status_code == 200


def test_game_108_scan_page_has_no_camera_while_off(client):
    _set(client, "off")
    html = client.get("/scan").text
    assert "Scanning is closed right now." in html
    assert "data-scanner" not in html
    assert "scanner.js" not in html


def test_game_102_scan_page_has_the_camera_while_on(client):
    html = client.get("/scan").text
    assert "data-scanner" in html
    assert "Scanning is" not in html


def test_ui_030_scan_keeps_one_back_link_while_off(client):
    _set(client, "off")
    html = client.get("/scan").text
    assert "Scanning is closed right now." in html
    assert html.count("Back to My Code") == 1


def test_game_108_own_notes_stay_readable_while_off(client):
    conn = connect(client.app.state.db_path)
    session = conn.execute(
        "INSERT INTO session (public_id, title, ended_at)"
        " VALUES ('pub-s1', 'Example Session 1', '2027-03-05T10:00:00Z')"
    ).lastrowid
    player = conn.execute(
        "SELECT id FROM player WHERE public_id = ?", (FAKE_PLAYER.public_id,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO takeaway (player_id, session_id, text) VALUES (?, ?, ?)",
        (player, session, "Example takeaway kept private by Test Player 1."),
    )
    conn.close()
    _set(client, "off")
    home = client.get("/").text
    # DEC-077: Write opens the notes while off, with no points pill.
    assert 'href="/journal"' in home
    assert f"+{load_config()['points']['journal_takeaway']}" not in home
    html = client.get("/journal").text
    assert "Example takeaway kept private by Test Player 1." in html
    assert '<span class="note-status">Just me</span>' in html
    # Nothing new or changed while off (GAME-108, DEC-076).
    assert disabled_button("Write a takeaway").search(html)
    assert 'href="/journal/new"' not in html
    assert "/visibility" not in html
