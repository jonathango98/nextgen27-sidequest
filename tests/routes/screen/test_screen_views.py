import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, screen_key, session
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.services import main_screen, points
from app.services.game_state import set_state
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030). The key has characters a link must encode.
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_SCREEN_KEY = "test-only screen&key/1"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")
CONFIG = load_config()
SCREEN_CFG = CONFIG["main_screen"]
BOOTH = CONFIG["points"]["booth_visit"]
PARTIALS = [f"/screen/{view}" for view in main_screen.VIEWS]


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "main-screen.db"


@pytest.fixture
def client(monkeypatch, db_path):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(screen_key.KEY_ENV, FAKE_SCREEN_KEY)
    with TestClient(
        create_app(), base_url="https://testserver", follow_redirects=False
    ) as c:
        conn = connect(db_path)
        create_account(conn, *ADMIN, "admin")
        create_account(conn, *USHER, "usher")
        conn.close()
        c.get("/staff/login")  # sets the CSRF cookie
        yield c


def _get(client, path, key=FAKE_SCREEN_KEY, **headers):
    params = {} if key is None else {screen_key.PARAM: key}
    return client.get(path, params=params, headers=headers)


def _set(db_path, state):
    conn = connect(db_path)
    try:
        set_state(conn, state)
    finally:
        conn.close()


def _log_in(client, username, password):
    response = client.post(
        "/staff/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
    )
    assert response.status_code == 303


def _pick(client, view, **headers):
    return client.post(
        "/admin/screen-off-view",
        data={"view": view, "csrf_token": client.cookies[csrf.COOKIE]},
        headers=headers,
    )


def _view(html):
    return re.search(r'data-view="([a-z]+)"', html).group(1)


def _next(html):
    return re.search(r'hx-get="/screen/([a-z]+)\?', html).group(1)


@pytest.mark.parametrize("path", ["/screen", *PARTIALS])
def test_arch_037_right_key_opens_the_main_screen(client, path):
    response = _get(client, path)
    assert response.status_code == 200
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-robots-tag"] == "noindex"


@pytest.mark.parametrize("path", ["/screen", *PARTIALS])
@pytest.mark.parametrize("key", [None, "", "test-only screen&key/2"])
def test_arch_037_missing_or_wrong_key_gets_404(client, path, key):
    assert _get(client, path, key).status_code == 404


def test_arch_037_no_key_set_on_the_server_means_404(client, monkeypatch):
    monkeypatch.delenv(screen_key.KEY_ENV)
    assert _get(client, "/screen").status_code == 404
    assert _get(client, "/screen", key="").status_code == 404


def test_arch_037_admin_login_does_not_open_the_screen_without_key(client):
    _log_in(client, *ADMIN)
    assert _get(client, "/screen", key=None).status_code == 404


def test_arch_037_screen_key_opens_no_staff_or_player_page(client):
    # The screen browser holds no login: staff pages ask for the staff login, player pages for
    # the player login (ARCH-035, DEC-061).
    _get(client, "/screen")
    for path, login in [
        ("/admin", "/staff/login"),
        ("/usher", "/staff/login"),
        ("/", "/login"),
        ("/code", "/login"),
    ]:
        response = client.get(path, params={screen_key.PARAM: FAKE_SCREEN_KEY})
        assert (response.status_code, response.headers["location"]) == (303, login)


def test_api_031_views_take_turns_every_rotate_seconds(client):
    html = _get(client, "/screen").text
    view = _view(html)
    assert view == main_screen.VIEWS[0]
    seen = [view]
    for _ in main_screen.VIEWS:
        assert f'hx-trigger="every {SCREEN_CFG["rotate_seconds"]}s"' in html
        html = _get(client, f"/screen/{_next(html)}", **{"HX-Request": "true"}).text
        assert "<html" not in html  # API-002: a partial, not the whole page
        seen.append(_view(html))
    assert seen == [*main_screen.VIEWS, main_screen.VIEWS[0]]


def test_arch_037_next_view_link_keeps_the_encoded_key(client):
    html = _get(client, "/screen").text
    link = re.search(r'hx-get="([^"]+)"', html).group(1).replace("&amp;", "&")
    # Following the link as written opens the next view, so the key survived encoding.
    assert client.get(link).status_code == 200


def test_ui_041_smallest_sizes_come_from_config(client):
    html = _get(client, "/screen").text
    assert f"--screen-text-min: {SCREEN_CFG['min_text_px_1080p']};" in html
    assert f"--screen-row-min: {SCREEN_CFG['min_row_px_1080p']}" in html


def test_dec_069_paused_game_keeps_the_screen_turning(client, db_path):
    _set(db_path, "paused")
    html = _get(client, "/screen/churches").text
    assert _view(html) == "churches"
    assert "Side Quest is offline" not in html


def test_ui_040_off_shows_offline_and_keeps_asking_for_the_first_view(client, db_path):
    _set(db_path, "off")
    html = _get(client, "/screen/takeaways").text
    assert _view(html) == "offline"
    assert "Side Quest is offline" in html
    assert _next(html) == main_screen.VIEWS[0]
    # Back on: the next turn shows the first view again (UI-040).
    _set(db_path, "on")
    assert _view(_get(client, f"/screen/{_next(html)}").text) == main_screen.VIEWS[0]


def test_ui_044_admin_picks_recap_for_the_off_screen(client, db_path):
    _set(db_path, "off")
    _log_in(client, *ADMIN)
    response = _pick(client, "recap", **{"HX-Request": "true"})
    assert response.status_code == 200
    assert '<section id="main-screen"' in response.text
    assert "<html" not in response.text
    assert 'data-off-view="recap"' in response.text
    assert _view(_get(client, "/screen").text) == "recap"


def test_ui_044_plain_pick_goes_back_to_the_console(client):
    _log_in(client, *ADMIN)
    response = _pick(client, "recap")
    assert (response.status_code, response.headers["location"]) == (303, "/admin")


def test_ui_044_unknown_off_view_is_refused(client):
    _log_in(client, *ADMIN)
    response = _pick(client, "leaderboard", **{"HX-Request": "true"})
    assert response.status_code == 400
    assert 'data-error-code="BAD_INPUT"' in response.text
    assert 'data-off-view="offline"' in response.text


def test_arch_038_off_view_pick_needs_the_csrf_token(client):
    _log_in(client, *ADMIN)
    response = client.post("/admin/screen-off-view", data={"view": "recap"})
    assert response.status_code == 400


def test_arch_035_usher_cannot_pick_the_off_view(client, db_path):
    _log_in(client, *USHER)
    response = _pick(client, "recap")
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text
    conn = connect(db_path)
    try:
        assert main_screen.off_view(conn) == "offline"
    finally:
        conn.close()


def test_arch_037_admin_console_shows_the_screen_link(client):
    _log_in(client, *ADMIN)
    html = client.get("/admin").text
    assert 'href="https://testserver/screen?k=test-only%20screen%26key%2F1"' in html
    assert 'rel="noreferrer"' in html


def test_arch_037_admin_console_says_when_the_key_is_not_set(client, monkeypatch):
    monkeypatch.delenv(screen_key.KEY_ENV)
    _log_in(client, *ADMIN)
    html = client.get("/admin").text
    assert "/screen?k=" not in html
    assert "not set up yet" in html


def test_arch_037_usher_console_never_shows_the_screen_link(client):
    _log_in(client, *USHER)
    html = client.get("/usher").text
    assert "/screen?k=" not in html
    assert 'id="main-screen"' not in html


def _add_player(db_path, n, church, last_name, earned, under_18=False):
    """Fake player (ENG-047) with join points, plus `earned` points from a booth."""
    conn = connect(db_path)
    try:
        conn.execute("INSERT OR IGNORE INTO church (name) VALUES (?)", (church,))
        player_id = conn.execute(
            "INSERT INTO player"
            " (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " SELECT ?, ?, ?, id, ?, 'not-a-real-hash' FROM church WHERE name = ?",
            (f"fake-{n}", f"Test{n}", last_name, int(under_18), church),
        ).lastrowid
        points.award_join(
            conn,
            player_id=player_id,
            amount=CONFIG["points"]["join"],
            while_paused=True,
        )
        points.award(
            conn,
            player_id=player_id,
            reason_code="booth_visit",
            amount=earned,
            source_type="booth",
            source_id=1,
        )
    finally:
        conn.close()


def test_game_086_player_board_shows_first_name_last_initial_and_church(
    client, db_path
):
    _add_player(db_path, 1, "Example Church A", "Kowalski", 2 * BOOTH, under_18=True)
    _add_player(db_path, 2, "Example Church B", "Nguyen", BOOTH)
    html = _get(client, "/screen/players").text
    # GAME-088: "Sam K." style, highest score first. SAFE-019: the under-18 player is listed.
    assert html.index("Test1 K.") < html.index("Test2 N.")
    assert "Example Church A" in html and "Example Church B" in html
    # SAFE-004: the full last name never reaches the screen.
    assert "Kowalski" not in html and "Nguyen" not in html
    assert "Coming soon" not in html


def test_game_081_church_board_shows_church_scores(client, db_path):
    _add_player(db_path, 1, "Example Church A", "Player 1", BOOTH)
    _add_player(db_path, 2, "Example Church B", "Player 2", 3 * BOOTH)
    html = _get(client, "/screen/churches").text
    assert html.index("Example Church B") < html.index("Example Church A")
    assert "Player 1" not in html and "Test1" not in html


@pytest.mark.parametrize("view", ["players", "churches"])
def test_game_087_empty_board_says_no_points_yet(client, view):
    html = _get(client, f"/screen/{view}").text
    assert "No points yet" in html
    assert "Coming soon" not in html


@pytest.mark.parametrize("view", ["players", "churches"])
def test_game_087_boards_stay_up_while_paused(client, db_path, view):
    _add_player(db_path, 1, "Example Church A", "Player 1", BOOTH)
    _set(db_path, "paused")
    html = _get(client, f"/screen/{view}").text
    assert _view(html) == view
    assert "Example Church A" in html


@pytest.mark.parametrize("view", ["players", "churches"])
def test_game_087_boards_never_show_while_off(client, db_path, view):
    _add_player(db_path, 1, "Example Church A", "Player 1", BOOTH)
    _set(db_path, "off")
    html = _get(client, f"/screen/{view}").text
    assert _view(html) == "offline"
    assert "Example Church A" not in html and "Test1" not in html
