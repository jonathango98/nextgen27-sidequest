import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.auth.password import verify_password
from app.db import connect, migrate
from app.main import create_app
from app.services.staff import (
    FIRST_ADMIN_PASSWORD_ENV,
    PREVIEW_ACCOUNTS,
    StaffAccountError,
    create_account,
    main,
    seed_preview,
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
