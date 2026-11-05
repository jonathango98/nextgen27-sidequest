import pytest
from fastapi.testclient import TestClient

from app.auth import csrf, session
from app.db import connect
from app.main import create_app
from app.services import qr
from app.services.staff import create_account

# Fake data only (ENG-047, SAFE-030).
FAKE_SESSION_KEY = "test-only-fake-session-key"
FAKE_QR_KEY = "test-only-fake-signing-key"
FAKE_PIN_HASH = "not-a-real-hash"
ADMIN = ("test-admin-1", "test password only 1")
USHER = ("test-usher-1", "test password only 2")
NAMED = "Example takeaway from Test Player 1, shared with a name."
ANON = "Example takeaway from Test Player 2, shared anonymously."
PRIVATE = "Example takeaway from Test Player 1, kept private."


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "admin-review.db"


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
        _seed_notes(conn)
        conn.close()
        c.get("/staff/login")  # sets the CSRF cookie
        yield c


def _seed_notes(conn):
    church = conn.execute(
        "INSERT INTO church (name) VALUES ('Example Church A')"
    ).lastrowid
    one, two = (
        conn.execute(
            "INSERT INTO player (public_id, first_name, last_name, church_id, is_under_18, pin_hash)"
            " VALUES (?, 'Test', ?, ?, 0, ?)",
            (f"pub-{n}", f"Player {n}", church, FAKE_PIN_HASH),
        ).lastrowid
        for n in (1, 2)
    )
    s = conn.execute(
        "INSERT INTO session (public_id, title, ended_at)"
        " VALUES ('pub-s1', 'Example Session 1', '2027-03-05T10:00:00Z')"
    ).lastrowid
    conn.executemany(
        "INSERT INTO takeaway (public_id, player_id, session_id, text, visibility, review_status)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("note-named", one, s, NAMED, "shared_named", "pending"),
            ("note-anon", two, s, ANON, "shared_anonymous", "pending"),
            ("note-private", one, s, PRIVATE, "private", "not_needed"),
        ],
    )


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


def _review(client, note, outcome, status="pending", **headers):
    return client.post(
        f"/admin/review/{note}",
        data={
            "outcome": outcome,
            "status": status,
            "csrf_token": client.cookies[csrf.COOKIE],
        },
        headers=headers,
    )


def _status(db_path, note):
    conn = connect(db_path)
    try:
        return conn.execute(
            "SELECT review_status FROM takeaway WHERE public_id = ?", (note,)
        ).fetchone()[0]
    finally:
        conn.close()


def _audit(db_path):
    conn = connect(db_path)
    try:
        return [
            tuple(r)
            for r in conn.execute(
                "SELECT actor_type, action, target_type FROM audit_log"
                " WHERE action LIKE 'review_%' ORDER BY id"
            )
        ]
    finally:
        conn.close()


def test_safe_007_waiting_notes_show_with_their_writer(client):
    _log_in(client, *ADMIN)
    html = client.get("/admin/review").text
    assert NAMED in html and ANON in html
    assert "Waiting (2)" in html
    # SAFE-009: admins see who wrote the anonymous note.
    assert "Test Player 2, Example Church A" in html
    assert 'Players see "Anonymous"' in html


def test_safe_029_private_notes_are_never_listed(client):
    _log_in(client, *ADMIN)
    for status in ("pending", "approved", "rejected", "hidden"):
        html = client.get(f"/admin/review?status={status}").text
        assert PRIVATE not in html
        assert "note-private" not in html


def test_safe_007_an_unknown_tab_shows_waiting(client):
    _log_in(client, *ADMIN)
    html = client.get("/admin/review?status=private").text
    assert 'aria-current="page">Waiting (2)' in html
    assert PRIVATE not in html


def test_safe_040_approve_writes_an_audit_row(client, db_path):
    _log_in(client, *ADMIN)
    response = _review(client, "note-named", "approve", **{"HX-Request": "true"})
    assert response.status_code == 200
    assert "Approved. Players can read it on All journals." in response.text
    assert 'id="review"' in response.text  # hx-select picks the list out of the page
    assert _status(db_path, "note-named") == "approved"
    assert _audit(db_path) == [("admin", "review_approve", "takeaway")]


def test_safe_040_reject_moves_it_to_the_rejected_tab(client, db_path):
    _log_in(client, *ADMIN)
    response = _review(client, "note-anon", "reject")
    assert response.status_code == 200
    assert ANON not in response.text  # gone from Waiting
    assert _status(db_path, "note-anon") == "rejected"
    assert ANON in client.get("/admin/review?status=rejected").text
    assert _audit(db_path) == [("admin", "review_reject", "takeaway")]


def test_safe_041_hide_an_approved_note(client, db_path):
    _log_in(client, *ADMIN)
    _review(client, "note-named", "approve")
    html = client.get("/admin/review?status=approved").text
    assert 'name="outcome" value="hide"' in html
    assert 'name="outcome" value="reject"' not in html
    response = _review(client, "note-named", "hide", status="approved")
    assert "Hidden. Players can&#39;t read it anymore." in response.text
    assert _status(db_path, "note-named") == "hidden"


def test_dec_076_approve_again_after_a_hide(client, db_path):
    _log_in(client, *ADMIN)
    _review(client, "note-named", "approve")
    _review(client, "note-named", "hide", status="approved")
    html = client.get("/admin/review?status=hidden").text
    assert "Approve again" in html
    _review(client, "note-named", "approve", status="hidden")
    assert _status(db_path, "note-named") == "approved"
    assert [a[1] for a in _audit(db_path)] == [
        "review_approve",
        "review_hide",
        "review_approve",
    ]


def test_safe_040_a_second_review_says_it_is_already_done(client, db_path):
    _log_in(client, *ADMIN)
    _review(client, "note-named", "approve")
    response = _review(client, "note-named", "reject")
    assert response.status_code == 409
    assert 'data-error-code="ALREADY_DONE"' in response.text
    assert _status(db_path, "note-named") == "approved"


def test_safe_029_a_private_note_cannot_be_reviewed(client, db_path):
    _log_in(client, *ADMIN)
    response = _review(client, "note-private", "approve")
    assert response.status_code == 404
    assert _status(db_path, "note-private") == "not_needed"
    assert _audit(db_path) == []


def test_safe_040_a_made_up_outcome_is_refused(client, db_path):
    _log_in(client, *ADMIN)
    response = _review(client, "note-named", "delete")
    assert response.status_code == 400
    assert _status(db_path, "note-named") == "pending"


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/admin/review"), ("post", "/admin/review/note-named")],
)
def test_game_110_usher_is_refused(client, db_path, method, path):
    _log_in(client, *USHER)
    if method == "get":
        response = client.get(path)
    else:
        response = _review(client, "note-named", "approve")
    assert response.status_code == 403
    assert 'data-error-code="WRONG_ROLE"' in response.text
    assert _status(db_path, "note-named") == "pending"


def test_arch_035_logged_out_goes_to_staff_login(client):
    response = client.get("/admin/review")
    assert (response.status_code, response.headers["location"]) == (
        303,
        "/staff/login",
    )


def test_arch_038_review_needs_csrf(client, db_path):
    _log_in(client, *ADMIN)
    response = client.post(
        "/admin/review/note-named", data={"outcome": "approve", "status": "pending"}
    )
    assert response.status_code == 400
    assert _status(db_path, "note-named") == "pending"


def test_safe_007_admin_console_links_to_review(client):
    _log_in(client, *ADMIN)
    assert 'href="/admin/review">Review notes</a>' in client.get("/admin").text


def test_safe_007_tab_counts_update_with_the_swapped_list(client):
    _log_in(client, *ADMIN)
    html = _review(client, "note-named", "approve", **{"HX-Request": "true"}).text
    review = html[html.index('id="review"') :]
    assert "Waiting (1)" in review and "Approved (1)" in review
