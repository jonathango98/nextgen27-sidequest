import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.auth.password import verify_password
from app.db import connect, migrate
from app.main import create_app
from app.services.staff import (
    FIRST_ADMIN_PASSWORD_ENV,
    PREVIEW_ACCOUNTS,
    USERNAME_MAX_CHARS,
    StaffAccountError,
    StaffAccountNotFound,
    add_account,
    create_account,
    list_accounts,
    main,
    seed_preview,
    set_active,
)

# Fake data only (ENG-047).
FAKE_PASSWORD = "test password only 1"


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def command_db(tmp_path, monkeypatch):
    path = tmp_path / "side-quest.db"
    monkeypatch.setenv("SQ_DB_PATH", str(path))
    monkeypatch.setenv(FIRST_ADMIN_PASSWORD_ENV, FAKE_PASSWORD)
    return path


def _accounts(path):
    conn = connect(path)
    try:
        return [dict(row) for row in conn.execute("SELECT * FROM staff_account")]
    finally:
        conn.close()


def test_arch_036_account_saved_with_a_slow_hash(conn):
    account_id = create_account(conn, "  test-usher-1 ", FAKE_PASSWORD, "usher")
    row = conn.execute(
        "SELECT * FROM staff_account WHERE id = ?", (account_id,)
    ).fetchone()
    assert row["username"] == "test-usher-1"
    assert row["role"] == "usher"
    assert row["is_active"] == 1
    assert FAKE_PASSWORD not in row["password_hash"]
    assert verify_password(FAKE_PASSWORD, row["password_hash"])


def test_arch_036_username_unique_ignoring_case(conn):
    assert create_account(conn, "test-admin-1", FAKE_PASSWORD, "admin") is not None
    assert create_account(conn, "TEST-ADMIN-1", "other password", "usher") is None
    rows = conn.execute("SELECT role FROM staff_account").fetchall()
    assert [row["role"] for row in rows] == ["admin"]


def test_arch_036_existing_account_is_never_changed(conn):
    create_account(conn, "test-admin-1", FAKE_PASSWORD, "admin")
    create_account(conn, "test-admin-1", "test password only 2", "admin")
    stored = conn.execute("SELECT password_hash FROM staff_account").fetchone()[0]
    assert verify_password(FAKE_PASSWORD, stored)


@pytest.mark.parametrize("role", ["player", "screen", "Admin", ""])
def test_arch_035_staff_role_is_usher_or_admin(conn, role):
    with pytest.raises(StaffAccountError):
        create_account(conn, "test-admin-1", FAKE_PASSWORD, role)


@pytest.mark.parametrize("role", ["player", "screen"])
def test_arch_035_database_refuses_other_roles(conn, role):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO staff_account (username, password_hash, role) VALUES (?, ?, ?)",
            ("test-admin-1", "not-a-real-hash", role),
        )


@pytest.mark.parametrize(
    ("username", "password"), [("   ", FAKE_PASSWORD), ("test-admin-1", "")]
)
def test_arch_036_empty_username_or_password_refused(conn, username, password):
    with pytest.raises(StaffAccountError):
        create_account(conn, username, password, "admin")
    assert conn.execute("SELECT count(*) FROM staff_account").fetchone()[0] == 0


def test_arch_036_create_admin_makes_an_admin(command_db, capsys):
    assert main(["create-admin", "test-admin-1"]) == 0
    assert "Admin test-admin-1 created." in capsys.readouterr().out
    [account] = _accounts(command_db)
    assert (account["username"], account["role"]) == ("test-admin-1", "admin")


def test_arch_036_create_admin_twice_makes_one(command_db, capsys):
    assert main(["create-admin", "test-admin-1"]) == 0
    assert main(["create-admin", "test-admin-1"]) == 0
    assert "already exists. Nothing changed." in capsys.readouterr().out
    assert len(_accounts(command_db)) == 1


def test_arch_036_password_never_in_output(command_db, capsys):
    main(["create-admin", "test-admin-1"])
    main(["create-admin", "test-admin-1"])
    out = capsys.readouterr()
    [account] = _accounts(command_db)
    for text in (out.out, out.err):
        assert FAKE_PASSWORD not in text
        assert account["password_hash"] not in text


def test_arch_036_missing_password_env_var_refuses(command_db, monkeypatch, capsys):
    monkeypatch.delenv(FIRST_ADMIN_PASSWORD_ENV)
    assert main(["create-admin", "test-admin-1"]) == 1
    assert FIRST_ADMIN_PASSWORD_ENV in capsys.readouterr().err
    assert not command_db.exists()


@pytest.mark.parametrize(
    "argv", [[], ["create-admin"], ["create-usher", "test-usher-1"]]
)
def test_arch_036_command_needs_create_admin_and_a_username(command_db, argv, capsys):
    assert main(argv) == 2
    assert "Usage" in capsys.readouterr().err


@pytest.fixture
def preview_passwords(monkeypatch):
    for _, _, password_env in PREVIEW_ACCOUNTS:
        monkeypatch.setenv(password_env, FAKE_PASSWORD)


def test_safe_031_preview_seed_makes_test_admin_and_usher(conn, preview_passwords):
    assert seed_preview(conn) == ["test-admin-1", "test-usher-1"]
    rows = conn.execute(
        "SELECT username, role, password_hash FROM staff_account"
    ).fetchall()
    assert {(row["username"], row["role"]) for row in rows} == {
        ("test-admin-1", "admin"),
        ("test-usher-1", "usher"),
    }
    assert all(verify_password(FAKE_PASSWORD, row["password_hash"]) for row in rows)


def test_safe_030_preview_seed_skips_an_account_without_a_password(conn, monkeypatch):
    monkeypatch.setenv("SQ_PREVIEW_ADMIN_PASSWORD", FAKE_PASSWORD)
    monkeypatch.delenv("SQ_PREVIEW_USHER_PASSWORD", raising=False)
    assert seed_preview(conn) == ["test-admin-1"]


def test_arch_036_preview_seed_never_changes_an_existing_account(
    conn, preview_passwords
):
    create_account(conn, "test-admin-1", "test password only 2", "usher")
    assert seed_preview(conn) == ["test-usher-1"]
    assert seed_preview(conn) == []
    row = conn.execute(
        "SELECT role, password_hash FROM staff_account WHERE username = 'test-admin-1'"
    ).fetchone()
    assert row["role"] == "usher"
    assert verify_password("test password only 2", row["password_hash"])


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ("nextgen27-sidequest-pr-35", {"test-admin-1", "test-usher-1"}),
        ("manual-pr-67", {"test-admin-1", "test-usher-1"}),
        ("staging", set()),
        ("production", set()),
    ],
)
def test_arch_017_app_start_seeds_staff_only_on_pr_previews(
    tmp_path, monkeypatch, preview_passwords, environment, expected
):
    db = tmp_path / "start.db"
    monkeypatch.setenv("SQ_DB_PATH", str(db))
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", environment)
    with TestClient(create_app()):
        pass
    assert {row["username"] for row in _accounts(db)} == expected


# admin.setup: an admin adds accounts and switches them off (ARCH-036, GAME-110, ARCH-050).


@pytest.fixture
def admin_id(conn):
    return create_account(conn, "test-admin-1", FAKE_PASSWORD, "admin")


def _audit_rows(conn):
    return [
        dict(r)
        for r in conn.execute(
            "SELECT actor_type, actor_id, action, target_type, target_id, reason"
            " FROM audit_log ORDER BY id"
        )
    ]


def _is_active(conn, account_id):
    return conn.execute(
        "SELECT is_active FROM staff_account WHERE id = ?", (account_id,)
    ).fetchone()[0]


def test_arch_036_admin_adds_an_account_with_an_audit_row(conn, admin_id):
    account_id = add_account(conn, " Test Usher ", FAKE_PASSWORD, "usher", admin_id)
    row = conn.execute(
        "SELECT * FROM staff_account WHERE id = ?", (account_id,)
    ).fetchone()
    assert (row["username"], row["role"], row["is_active"]) == (
        "Test Usher",
        "usher",
        1,
    )
    assert verify_password(FAKE_PASSWORD, row["password_hash"])
    assert _audit_rows(conn) == [
        {
            "actor_type": "admin",
            "actor_id": admin_id,
            "action": "staff_add",
            "target_type": "staff_account",
            "target_id": account_id,
            "reason": None,
        }
    ]


def test_arch_051_staff_audit_row_has_no_username_or_password(conn, admin_id):
    add_account(conn, "Test Usher", FAKE_PASSWORD, "usher", admin_id)
    text = repr(_audit_rows(conn))
    assert "Test Usher" not in text
    assert FAKE_PASSWORD not in text


@pytest.mark.parametrize("role", ["usher", "admin"])
def test_arch_035_admin_adds_an_usher_or_an_admin(conn, admin_id, role):
    account_id = add_account(conn, "Test Staff 2", FAKE_PASSWORD, role, admin_id)
    assert (
        conn.execute(
            "SELECT role FROM staff_account WHERE id = ?", (account_id,)
        ).fetchone()[0]
        == role
    )


@pytest.mark.parametrize(
    ("username", "password", "role"),
    [
        ("", FAKE_PASSWORD, "usher"),
        ("   ", FAKE_PASSWORD, "usher"),
        ("Test Usher", "", "usher"),
        ("Test Usher", FAKE_PASSWORD, "screen"),
        ("x" * (USERNAME_MAX_CHARS + 1), FAKE_PASSWORD, "usher"),
    ],
)
def test_arch_036_add_refuses_a_bad_form_and_saves_nothing(
    conn, admin_id, username, password, role
):
    with pytest.raises(StaffAccountError):
        add_account(conn, username, password, role, admin_id)
    assert len(list_accounts(conn)) == 1
    assert _audit_rows(conn) == []


def test_arch_036_add_refuses_a_taken_username_ignoring_case(conn, admin_id):
    add_account(conn, "Test Usher", FAKE_PASSWORD, "usher", admin_id)
    with pytest.raises(StaffAccountError, match="already an account"):
        add_account(conn, "test usher", "other password", "admin", admin_id)
    assert len(list_accounts(conn)) == 2
    assert [r["action"] for r in _audit_rows(conn)] == ["staff_add"]


def test_ops_042_admin_switches_an_account_off_and_on(conn, admin_id):
    usher_id = add_account(conn, "Test Usher", FAKE_PASSWORD, "usher", admin_id)
    assert set_active(conn, usher_id, False, admin_id) is True
    assert _is_active(conn, usher_id) == 0
    assert set_active(conn, usher_id, True, admin_id) is True
    assert _is_active(conn, usher_id) == 1
    rows = _audit_rows(conn)
    assert [(r["action"], r["target_id"]) for r in rows] == [
        ("staff_add", usher_id),
        ("staff_switch_off", usher_id),
        ("staff_switch_on", usher_id),
    ]


def test_ops_042_switching_to_the_same_state_writes_nothing(conn, admin_id):
    usher_id = add_account(conn, "Test Usher", FAKE_PASSWORD, "usher", admin_id)
    set_active(conn, usher_id, False, admin_id)
    assert set_active(conn, usher_id, False, admin_id) is False
    assert [r["action"] for r in _audit_rows(conn)] == ["staff_add", "staff_switch_off"]


def test_arch_036_admin_cannot_switch_off_their_own_account(conn, admin_id):
    with pytest.raises(StaffAccountError, match="your own account"):
        set_active(conn, admin_id, False, admin_id)
    assert _is_active(conn, admin_id) == 1
    assert _audit_rows(conn) == []


def test_arch_036_admin_can_switch_off_another_admin(conn, admin_id):
    other = add_account(conn, "Test Admin 2", FAKE_PASSWORD, "admin", admin_id)
    assert set_active(conn, other, False, admin_id) is True
    assert _is_active(conn, other) == 0


def test_arch_036_switching_a_missing_account_is_not_found(conn, admin_id):
    with pytest.raises(StaffAccountNotFound):
        set_active(conn, admin_id + 99, False, admin_id)


def test_arch_036_list_shows_switched_on_accounts_first(conn, admin_id):
    usher_id = add_account(conn, "Test Usher", FAKE_PASSWORD, "usher", admin_id)
    add_account(conn, "Test Usher 2", FAKE_PASSWORD, "usher", admin_id)
    set_active(conn, usher_id, False, admin_id)
    assert [(a.username, a.role, a.is_active) for a in list_accounts(conn)] == [
        ("test-admin-1", "admin", True),
        ("Test Usher 2", "usher", True),
        ("Test Usher", "usher", False),
    ]
