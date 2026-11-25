import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session
from app.db import connect
from app.main import create_app
from app.services import audit, qr
from app.services.connections import ACTIVITY_ROWS, PREVIEW_PAIRS, seed_preview_activity
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
FAKE_PIN_HASH = "not-a-real-hash"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")
PAGES = ("/admin/audit", "/admin/activity")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "admin-audit.db"


@pytest.fixture
def client(monkeypatch, db_path):
    monkeypatch.setenv("SQ_DB_PATH", str(db_path))
    monkeypatch.setenv(session.KEY_ENV, FAKE_SESSION_KEY)
    monkeypatch.setenv(qr.KEY_ENV, FAKE_QR_KEY)
    with TestClient(
        create_app(), base_url="https://testserver", follow_redirects=False
    ) as c:
        conn = connect(db_path)
        create_account(conn, *ADMIN, "admin")
        create_account(conn, *USHER, "usher")
        conn.close()
        c.get("/staff/login")  # sets the CSRF cookie
        yield c


@pytest.fixture
def conn(client, db_path):
    c = connect(db_path)
    yield c
    c.close()


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


def _players(conn, *names):
    church_a = conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church A')"
    ).lastrowid
    return [
        conn.execute(
            "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " VALUES (?, 'Test', ?, ?, 0, ?)",
            (f"pub-{last}", last, church_a, FAKE_PIN_HASH),
        ).lastrowid
        for last in names
    ]


def _connect(conn, a, b, at):
    low, high = sorted((a, b))
    conn.execute(
        "INSERT INTO connection (player_low_id, player_high_id, scanner_id, is_same_church, created_at)"
        " VALUES (?, ?, ?, 1, ?)",
        (low, high, a, at),
    )


def test_arch_050_admin_sees_who_did_what_to_whom_and_when(client, conn):
    (player,) = _players(conn, "Player 1")
    admin_id = conn.execute(
        "SELECT id FROM staff_account WHERE username = ?", (ADMIN[0],)
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO audit_log (actor_type, actor_id, action, target_type, target_id, reason, created_at)"
        " VALUES ('admin', ?, 'pin_reset', 'player', ?, 'Checked badge', '2027-03-06T01:05:09Z')",
        (admin_id, player),
    )
    audit.record(conn, actor_type="system", actor_id=None, action="pause")
    _log_in(client, *ADMIN)
    html = client.get("/admin/audit").text
    assert "pin reset" in html
    assert f"{ADMIN[0]} (admin)" in html
    # GAME-112 style: first name, last initial, and church.
    assert "Test P., Example Church A" in html
    assert "Checked badge" in html
    # GAME-105: venue time (Houston, UTC-6 in early March).
    assert "Fri Mar 5, 7:05:09 PM" in html
    # Newest first.
    assert html.index("<strong>pause</strong>") < html.index(
        "<strong>pin reset</strong>"
    )


def test_arch_051_log_page_never_shows_a_full_last_name(client, conn):
    (player,) = _players(conn, "Lastname")
    audit.record(conn, actor_type="player", actor_id=player, action="takeaway_share")
    _log_in(client, *ADMIN)
    html = client.get("/admin/audit").text
    assert "Test L., Example Church A" in html
    assert "Lastname" not in html


def test_arch_050_points_rows_show_who_got_the_points(client, conn):
    (player,) = _players(conn, "Player 1")
    ledger = conn.execute(
        "INSERT INTO point_ledger (player_id, amount, reason_code, source_type, source_id)"
        " VALUES (?, 5, 'join', 'player', ?)",
        (player, player),
    ).lastrowid
    audit.record(
        conn,
        actor_type="system",
        actor_id=None,
        action="points_award",
        target_type="point_ledger",
        target_id=ledger,
    )
    _log_in(client, *ADMIN)
    html = client.get("/admin/audit").text
    assert "<strong>points award</strong> · Test P., Example Church A" in html
    assert "point ledger" not in html


def test_arch_050_older_link_shows_the_next_page(client, conn):
    for _ in range(audit.PAGE_ROWS + 1):
        audit.record(conn, actor_type="system", actor_id=None, action="pause")
    first_id = conn.execute("SELECT min(id) AS id FROM audit_log").fetchone()["id"]
    _log_in(client, *ADMIN)
    html = client.get("/admin/audit").text
    assert html.count("data-entry=") == audit.PAGE_ROWS
    assert f'data-entry="{first_id}"' not in html
    older = html.split('href="/admin/audit?before=')[1].split('"')[0]
    html = client.get(f"/admin/audit?before={older}").text
    assert html.count("data-entry=") == 1
    assert f'data-entry="{first_id}"' in html
    assert "?before=" not in html


@pytest.mark.parametrize("before", ["abc", "-1", "1.5"])
def test_arch_050_bad_older_value_shows_the_newest_page(client, conn, before):
    audit.record(conn, actor_type="system", actor_id=None, action="pause")
    _log_in(client, *ADMIN)
    response = client.get(f"/admin/audit?before={before}")
    assert response.status_code == 200
    assert response.text.count("data-entry=") == 1


@pytest.mark.parametrize("path", PAGES)
def test_arch_050_usher_is_refused(client, path):
    _log_in(client, *USHER)
    response = client.get(path)
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text


@pytest.mark.parametrize("path", PAGES)
def test_arch_050_player_and_logged_out_are_sent_to_staff_login(client, conn, path):
    assert client.get(path).headers["location"] == "/staff/login"
    _players(conn, "Player 1")
    client.cookies.set(
        session.COOKIE, f"pub-Player 1.{session.sign('session', 'pub-Player 1')}"
    )
    assert client.get(path).headers["location"] == "/staff/login"


def test_arch_050_console_has_a_log_tile(client):
    _log_in(client, *ADMIN)
    assert 'href="/admin/audit"' in client.get("/admin").text


def test_arch_062_most_connections_first_and_faster_wins_a_tie(client, conn):
    a, b, c, d, e = _players(conn, "Alpha", "Bravo", "Charlie", "Delta", "Echo")
    # Alpha: 3 connections over 4 minutes.
    _connect(conn, a, b, "2027-03-06T01:00:00Z")
    _connect(conn, a, c, "2027-03-06T01:02:00Z")
    _connect(conn, a, d, "2027-03-06T01:04:00Z")
    # Echo: 2 connections over 1 minute. Bravo: 2 over 60 minutes.
    _connect(conn, e, c, "2027-03-06T02:00:00Z")
    _connect(conn, e, d, "2027-03-06T02:01:00Z")
    _connect(conn, b, c, "2027-03-06T02:00:00Z")
    _log_in(client, *ADMIN)
    html = client.get("/admin/activity").text
    order = [html.index(f"Test {x}., Example Church A") for x in "AEB"]
    assert order == sorted(order)
    assert "Over 4 min" in html
    assert "Lastname" not in html and "Alpha" not in html  # ARCH-051: initial only


def test_arch_062_activity_lists_a_limited_number(client, conn):
    ids = _players(conn, *[f"P{n}" for n in range(ACTIVITY_ROWS + 2)])
    for other in ids[1:]:
        _connect(conn, ids[0], other, "2027-03-06T01:00:00Z")
    _log_in(client, *ADMIN)
    html = client.get("/admin/activity").text
    assert html.count("data-busy") == ACTIVITY_ROWS
    # One connection has no time span, so only the busy player shows one.
    assert "<strong>1</strong> connection ·" in html
    assert html.count("Over ") == 1


def test_eng_113_preview_activity_connects_only_the_leaderboard_players(conn):
    church = conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church A')"
    ).lastrowid
    for n in range(1, 7):
        conn.execute(
            "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " VALUES (?, 'Test', ?, ?, 0, ?)",
            (f"pub-{n}", f"Player {n}", church, FAKE_PIN_HASH),
        )
    assert seed_preview_activity(conn) == len(PREVIEW_PAIRS)
    assert seed_preview_activity(conn) == 0  # a restart adds nothing twice
    touched = conn.execute(
        "SELECT count(*) AS n FROM connection c JOIN player p"
        " ON p.id IN (c.player_low_id, c.player_high_id)"
        " WHERE p.last_name IN ('Player 1', 'Player 2')"
    ).fetchone()["n"]
    assert touched == 0
    assert conn.execute("SELECT count(*) AS n FROM point_ledger").fetchone()["n"] == 0
