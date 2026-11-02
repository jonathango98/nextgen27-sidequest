import re

import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session, signup
from app.config import load_config
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.game_state import set_state
from app.services.points import award
from tests.conftest import make_fake_pin

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
CHURCHES = ("Example Church A", "Example Church B")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "join.db"


@pytest.fixture
def client(monkeypatch, db_path):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    # https, so the Secure cookies are kept and sent back (ARCH-034).
    with TestClient(create_app(), base_url="https://testserver") as c:
        conn = connect(db_path)
        conn.executemany(
            "INSERT INTO church (name) VALUES (?)", [(n,) for n in CHURCHES]
        )
        conn.close()
        c.get("/join")  # sets the CSRF cookie
        yield c


@pytest.fixture
def church_a(db_path):
    conn = connect(db_path)
    row = conn.execute(
        "SELECT id FROM church WHERE name = ?", (CHURCHES[0],)
    ).fetchone()
    conn.close()
    return str(row["id"])


@pytest.fixture
def details(church_a):
    return {
        "first_name": "Test",
        "last_name": "Player 1",
        "church_id": church_a,
        "age_18_plus": "yes",
    }


@pytest.fixture
def join_points():
    return load_config()["points"]["join"]  # AI-013: never hardcode a game number


def _post(client, data, htmx=False):
    headers = {"HX-Request": "true"} if htmx else {}
    token = client.cookies.get(csrf.COOKIE)
    return client.post(
        "/join",
        data={"csrf_token": token, **data},
        headers=headers,
        follow_redirects=False,
    )


def _players(db_path):
    conn = connect(db_path)
    rows = conn.execute("SELECT * FROM player").fetchall()
    conn.close()
    return rows


def _error_code(response):
    match = re.search(r'data-error-code="([A-Z_]+)"', response.text)
    return match and match.group(1)


def test_safe_002_join_form_has_only_the_listed_fields(client):
    page = client.get("/join").text
    form = page[page.index("<form") : page.index("</form>")]
    names = set(re.findall(r'<(?:input|select)[^>]* name="([a-z_0-9]+)"', form))
    assert names == {
        "csrf_token",
        "step",
        "first_name",
        "last_name",
        "church_id",
        "age_18_plus",
    }
    assert "Are you 18 or older?" in page
    assert "under 18" not in page


def test_safe_002_church_list_comes_from_the_database(client):
    page = client.get("/join").text
    for name in CHURCHES:
        assert f">{name}</option>" in page


def test_arch_038_post_without_csrf_token_refused(client, details, db_path):
    response = client.post("/join", data={"step": "details", **details})
    assert response.status_code == 400
    assert _error_code(response) == "BAD_INPUT"


def test_arch_038_post_with_wrong_csrf_token_refused(
    client, details, fake_pin, db_path
):
    data = {"step": "pin", **details, "pin": fake_pin, "pin_again": fake_pin}
    response = client.post("/join", data={"csrf_token": "wrong", **data})
    assert response.status_code == 400
    assert _players(db_path) == []


def test_api_004_csrf_token_accepted_from_htmx_header(client, details):
    token = client.cookies.get(csrf.COOKIE)
    response = client.post(
        "/join",
        data={"step": "details", **details},
        headers={"HX-Request": "true", csrf.HEADER: token},
    )
    assert response.status_code == 200


def test_api_002_details_step_returns_pin_step_partial_for_htmx(client, details):
    response = _post(client, {"step": "details", **details}, htmx=True)
    assert response.status_code == 200
    assert 'name="pin"' in response.text and 'name="pin_again"' in response.text
    assert "<html" not in response.text


def test_api_007_details_step_works_without_javascript(client, details):
    response = _post(client, {"step": "details", **details})
    assert response.status_code == 200
    assert "<html" in response.text and 'name="pin"' in response.text


@pytest.mark.parametrize(
    "missing", ["first_name", "last_name", "church_id", "age_18_plus"]
)
def test_safe_002_every_field_is_required(client, details, missing):
    response = _post(client, {"step": "details", **details, missing: ""}, htmx=True)
    assert response.status_code == 400
    assert _error_code(response) == "BAD_INPUT"
    assert 'name="pin"' not in response.text


def test_ui_032_typed_values_stay_after_an_error(client, details):
    response = _post(client, {"step": "details", **details, "church_id": ""}, htmx=True)
    assert 'value="Test"' in response.text and 'value="Player 1"' in response.text


def test_safe_002_unknown_church_refused(client, details):
    response = _post(
        client, {"step": "details", **details, "church_id": "999"}, htmx=True
    )
    assert response.status_code == 400


def test_safe_021_pins_must_match(client, details, fake_pin, cfg_auth, db_path):
    other = make_fake_pin(cfg_auth["pin_digits"], start=5)
    data = {"step": "pin", **details, "pin": fake_pin, "pin_again": other}
    response = _post(client, data, htmx=True)
    assert response.status_code == 400
    assert 'name="pin"' in response.text
    assert _players(db_path) == []


def test_safe_021_pin_must_have_configured_length(client, details, fake_pin, db_path):
    short = fake_pin[:-1]
    data = {"step": "pin", **details, "pin": short, "pin_again": short}
    assert _post(client, data, htmx=True).status_code == 400
    assert _players(db_path) == []


def test_safe_002_join_creates_player_and_logs_in(client, details, fake_pin, db_path):
    data = {
        "step": "pin",
        **details,
        "first_name": "  Test ",
        "pin": fake_pin,
        "pin_again": fake_pin,
    }
    response = _post(client, data)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert session.COOKIE in response.headers["set-cookie"]

    [player] = _players(db_path)
    assert player["first_name"] == "Test"  # DATA-016: trimmed
    assert player["is_under_18"] == 0
    assert (
        player["pin_hash"].startswith("scrypt$") and fake_pin not in player["pin_hash"]
    )
    assert len(player["public_id"]) >= 12 and player["public_id"].isalnum()

    assert client.get("/code").status_code == 200  # get_current_player now finds them


def test_safe_002_not_18_plus_saved_as_under_18(client, details, fake_pin, db_path):
    data = {
        "step": "pin",
        **details,
        "age_18_plus": "no",
        "pin": fake_pin,
        "pin_again": fake_pin,
    }
    _post(client, data)
    assert _players(db_path)[0]["is_under_18"] == 1


def test_safe_002_18_plus_saved_as_adult(client, details, fake_pin, db_path):
    data = {"step": "pin", **details, "pin": fake_pin, "pin_again": fake_pin}
    _post(client, data)
    assert _players(db_path)[0]["is_under_18"] == 0


def test_safe_002_old_under_18_field_refused(client, details, fake_pin, db_path):
    # DEC-034: a page loaded before the change sends "under_18"; never guess its meaning.
    old = {k: v for k, v in details.items() if k != "age_18_plus"}
    data = {
        "step": "pin",
        **old,
        "under_18": "yes",
        "pin": fake_pin,
        "pin_again": fake_pin,
    }
    response = _post(client, data, htmx=True)
    assert response.status_code == 400
    assert _players(db_path) == []


def test_api_002_htmx_join_redirects_with_header(client, details, fake_pin):
    data = {"step": "pin", **details, "pin": fake_pin, "pin_again": fake_pin}
    response = _post(client, data, htmx=True)
    assert response.status_code == 204
    assert response.headers["hx-redirect"] == "/"


def test_safe_021_pin_never_sent_back(client, details, fake_pin):
    data = {"step": "pin", **details, "pin": fake_pin, "pin_again": fake_pin[:-1]}
    responses = [_post(client, data, htmx=True), _post(client, data)]
    for response in responses:
        assert fake_pin not in response.text


@pytest.mark.parametrize("step", ["details", "pin"])
def test_arch_033_same_name_same_church_refused(
    client, details, fake_pin, db_path, step
):
    data = {"step": "pin", **details, "pin": fake_pin, "pin_again": fake_pin}
    _post(client, data)
    client.cookies.delete(session.COOKIE)
    again = {**data, "step": step, "first_name": "TEST", "last_name": "player 1"}
    response = _post(client, again, htmx=True)
    assert response.status_code == 409
    assert _error_code(response) == "NAME_TAKEN"
    assert len(_players(db_path)) == 1


def test_arch_034_logged_in_player_skips_join(client, details, fake_pin):
    _post(client, {"step": "pin", **details, "pin": fake_pin, "pin_again": fake_pin})
    response = client.get("/join", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_arch_034_signed_cookie_for_unknown_player_is_not_logged_in(client):
    value = f"nobody00000x.{session.sign('session', 'nobody00000x')}"
    client.cookies.set(session.COOKIE, value)
    assert client.get("/code", follow_redirects=False).status_code == 303


def test_ui_032_back_from_pin_step_keeps_the_details(
    client, details, fake_pin, db_path
):
    response = _post(
        client,
        {**details, "step": "pin", "pin": fake_pin, "pin_again": fake_pin, "back": "1"},
        htmx=True,
    )
    assert response.status_code == 200
    assert 'name="pin"' not in response.text  # back on step 1
    assert 'value="Test"' in response.text
    assert 'value="Player 1"' in response.text
    assert re.search(rf'value="{details["church_id"]}"\s+selected', response.text)
    assert re.search(r'value="yes"\s+checked', response.text)
    assert fake_pin not in response.text  # SAFE-021: the PIN is never sent back
    assert _players(db_path) == []  # nothing saved


def test_api_007_back_works_without_javascript(client, details, db_path):
    response = _post(client, {**details, "step": "pin", "back": "1"})
    assert response.status_code == 200
    assert 'value="Player 1"' in response.text
    assert _players(db_path) == []


def _join(client, details, pin, htmx=False):
    data = {"step": "pin", **details, "pin": pin, "pin_again": pin}
    return _post(client, data, htmx=htmx)


def _ledger(db_path):
    conn = connect(db_path)
    rows = conn.execute("SELECT * FROM point_ledger").fetchall()
    conn.close()
    return rows


def _set_state(db_path, state):
    conn = connect(db_path)
    set_state(conn, state)
    conn.close()


def test_game_040_join_pays_configured_points_once(
    client, details, fake_pin, db_path, join_points
):
    _join(client, details, fake_pin)
    [row] = _ledger(db_path)
    assert row["amount"] == join_points
    assert row["player_id"] == _players(db_path)[0]["id"]


def test_game_040_refused_second_join_pays_nothing(client, details, fake_pin, db_path):
    _join(client, details, fake_pin)
    client.cookies.delete(session.COOKIE)
    assert _join(client, details, fake_pin).status_code == 409
    assert len(_ledger(db_path)) == 1


def test_game_044_join_paid_while_paused(
    client, details, fake_pin, db_path, join_points
):
    _set_state(db_path, "paused")
    assert _join(client, details, fake_pin).status_code == 303
    assert [row["amount"] for row in _ledger(db_path)] == [join_points]


def test_game_102_join_still_works_when_config_says_no_points_while_paused(
    client, details, fake_pin, db_path
):
    config = client.app.state.config
    client.app.state.config = {**config, "join": {"points_while_paused": False}}
    _set_state(db_path, "paused")
    assert _join(client, details, fake_pin).status_code == 303
    assert len(_players(db_path)) == 1
    assert _ledger(db_path) == []


def test_game_108_join_refused_while_off_saves_nothing(
    client, details, fake_pin, db_path
):
    _set_state(db_path, "off")
    response = _join(client, details, fake_pin, htmx=True)
    assert response.status_code == 423
    assert _error_code(response) == "GAME_OFF"
    assert session.COOKIE not in response.headers.get("set-cookie", "")
    assert _players(db_path) == []
    assert _ledger(db_path) == []


def test_ui_032_typed_values_stay_when_join_refused_while_off(
    client, details, fake_pin, db_path
):
    _set_state(db_path, "off")
    response = _join(client, details, fake_pin, htmx=True)
    assert 'value="Test"' in response.text and 'value="Player 1"' in response.text
    assert fake_pin not in response.text  # SAFE-021


def test_arch_040_failed_points_award_saves_no_player(
    client, details, fake_pin, db_path
):
    # The player and their points save together, or neither does.
    config = client.app.state.config
    conn = connect(db_path)
    d = signup.Details("Test", "Player 2", int(details["church_id"]), False)
    bad = {**config, "points": {**config["points"], "join": 0}}
    with pytest.raises(ValueError):
        signup.create_player(conn, d, fake_pin, bad)
    assert not conn.in_transaction
    conn.close()
    assert _players(db_path) == []


def test_arch_013_pin_hashed_before_taking_the_write_lock(
    client, details, fake_pin, db_path, monkeypatch
):
    conn = connect(db_path)
    seen = []
    real_hash = signup.pins.hash_pin

    def spy(pin):
        seen.append(conn.in_transaction)
        return real_hash(pin)

    monkeypatch.setattr(signup.pins, "hash_pin", spy)
    d = signup.Details("Test", "Player 2", int(details["church_id"]), False)
    signup.create_player(conn, d, fake_pin, client.app.state.config)
    conn.close()
    assert seen == [False]


def test_data_030_home_shows_real_score(client, details, fake_pin, join_points):
    _join(client, details, fake_pin)
    assert f"<h1>{join_points} points</h1>" in client.get("/").text


def test_data_030_score_is_read_from_the_ledger_each_time(
    client, details, fake_pin, db_path, join_points
):
    _join(client, details, fake_pin)
    assert f"<h1>{join_points} points</h1>" in client.get("/").text
    conn = connect(db_path)
    award(
        conn,
        player_id=_players(db_path)[0]["id"],
        reason_code="connect_other_church",
        amount=join_points,
        source_type="connection",
        source_id=1,
    )
    conn.close()
    assert f"<h1>{2 * join_points} points</h1>" in client.get("/").text


def test_game_040_logging_in_and_refreshing_do_not_add_points(
    client, details, fake_pin, db_path, join_points
):
    _join(client, details, fake_pin)
    client.cookies.delete(session.COOKIE)
    response = client.post(
        "/login",
        data={
            "csrf_token": client.cookies.get(csrf.COOKIE),
            "first_name": details["first_name"],
            "last_name": details["last_name"],
            "church_id": details["church_id"],
            "pin": fake_pin,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    for _ in range(3):
        assert f"<h1>{join_points} points</h1>" in client.get("/").text
    assert len(_ledger(db_path)) == 1
