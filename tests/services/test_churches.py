import io

import pytest
from fastapi.testclient import TestClient

from app.db import connect, migrate
from app.main import create_app
from app.services.churches import (
    EXAMPLE_CHURCHES,
    NAME_MAX_CHARS,
    ChurchListError,
    ChurchNotFound,
    add_church,
    is_preview,
    list_all,
    load,
    main,
    parse,
    rename_church,
    seed_examples,
)
from app.services.staff import create_account

# Fake data only (ENG-047).
CSV = "name\nExample Church A\n  Example Church B  \n\n"


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "side-quest.db")
    migrate(conn)
    yield conn
    conn.close()


def _names(conn):
    return sorted(r["name"] for r in conn.execute("SELECT name FROM church"))


def test_safe_002_loads_trimmed_names_and_skips_blank_rows(conn):
    assert load(conn, parse(CSV)) == ["Example Church A", "Example Church B"]
    assert _names(conn) == ["Example Church A", "Example Church B"]


def test_safe_002_loading_twice_adds_only_new_churches(conn):
    load(conn, parse(CSV))
    assert load(conn, parse(CSV + "Example Church C\n")) == ["Example Church C"]
    assert len(_names(conn)) == 3


@pytest.mark.parametrize(
    "text", ["", "church\nExample Church A\n", "name,region\nA,B\n"]
)
def test_safe_002_header_must_be_name_only(text):
    with pytest.raises(ChurchListError):
        parse(text)


def test_safe_002_row_with_two_columns_refused():
    with pytest.raises(ChurchListError):
        parse("name\nExample Church A,North\n")


def test_dec_011_near_duplicate_in_file_refused_and_nothing_loaded(conn):
    with pytest.raises(ChurchListError):
        load(conn, parse("name\nExample Church A\nexample  church a\n"))
    assert _names(conn) == []


def test_dec_011_near_duplicate_of_loaded_church_refused_and_nothing_loaded(conn):
    load(conn, parse(CSV))
    with pytest.raises(ChurchListError):
        load(conn, parse("name\nExample Church C\nEXAMPLE CHURCH A\n"))
    assert _names(conn) == ["Example Church A", "Example Church B"]


def test_safe_002_command_reads_stdin(tmp_path, monkeypatch, capsys):
    db = tmp_path / "cmd.db"
    monkeypatch.setenv("SQ_DB_PATH", str(db))
    monkeypatch.setattr("sys.stdin", io.StringIO("﻿" + CSV))
    assert main(["-"]) == 0
    assert "Added 2 churches. 2 in the list now." in capsys.readouterr().out
    assert _names(connect(db)) == ["Example Church A", "Example Church B"]


def test_safe_002_command_reports_refusal(tmp_path, monkeypatch, capsys):
    path = tmp_path / "bad.csv"
    path.write_text("church\nExample Church A\n", encoding="utf-8")
    monkeypatch.setenv("SQ_DB_PATH", str(tmp_path / "cmd.db"))
    assert main([str(path)]) == 1
    assert "Nothing loaded" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("name", "preview"),
    [
        ("nextgen27-sidequest-pr-35", True),
        ("nextgen27-sidequest-pr-7", True),
        ("production", False),
        ("staging", False),
        ("pr-preview", False),
        ("", False),
        (None, False),
    ],
)
def test_arch_017_only_pr_previews_count_as_preview(name, preview):
    assert is_preview(name) is preview


def test_safe_031_seed_adds_fake_churches_when_empty(conn):
    assert seed_examples(conn) == EXAMPLE_CHURCHES
    assert _names(conn) == EXAMPLE_CHURCHES


def test_safe_031_seed_leaves_a_loaded_list_alone(conn):
    load(conn, ["Example Church Z"])
    assert seed_examples(conn) == []
    assert _names(conn) == ["Example Church Z"]


@pytest.mark.parametrize(
    ("environment", "expected"),
    [("nextgen27-sidequest-pr-35", EXAMPLE_CHURCHES), ("production", [])],
)
def test_arch_017_app_start_seeds_only_pr_previews(
    tmp_path, monkeypatch, environment, expected
):
    db = tmp_path / "start.db"
    monkeypatch.setenv("SQ_DB_PATH", str(db))
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", environment)
    with TestClient(create_app()):
        pass
    assert _names(connect(db)) == expected


# admin.setup: an admin adds and renames churches (SAFE-002, GAME-110, ARCH-050).


@pytest.fixture
def admin_id(conn):
    return create_account(conn, "test-admin-1", "test password only 1", "admin")


def _audit_rows(conn):
    return [
        (r["actor_type"], r["actor_id"], r["action"], r["target_type"], r["target_id"])
        for r in conn.execute("SELECT * FROM audit_log ORDER BY id")
    ]


def test_safe_002_admin_adds_a_church_with_an_audit_row(conn, admin_id):
    church_id = add_church(conn, "  Example   Church D ", admin_id)
    assert [(c.id, c.name) for c in list_all(conn)] == [(church_id, "Example Church D")]
    assert _audit_rows(conn) == [("admin", admin_id, "church_add", "church", church_id)]


@pytest.mark.parametrize(
    "name",
    ["", "   ", "x" * (NAME_MAX_CHARS + 1), "example church a", "Example  Church A"],
)
def test_safe_002_add_refuses_an_empty_long_or_look_alike_name(conn, admin_id, name):
    load(conn, ["Example Church A"])
    with pytest.raises(ChurchListError):
        add_church(conn, name, admin_id)
    assert _names(conn) == ["Example Church A"]
    assert _audit_rows(conn) == []


def test_game_018_rename_keeps_the_church_id(conn, admin_id):
    church_id = add_church(conn, "Example Church D", admin_id)
    assert rename_church(conn, church_id, "Example Church E", admin_id) is True
    assert [(c.id, c.name) for c in list_all(conn)] == [(church_id, "Example Church E")]
    assert _audit_rows(conn)[-1] == (
        "admin",
        admin_id,
        "church_rename",
        "church",
        church_id,
    )


def test_safe_002_rename_can_fix_only_the_case(conn, admin_id):
    church_id = add_church(conn, "Example church d", admin_id)
    assert rename_church(conn, church_id, "Example Church D", admin_id) is True
    assert _names(conn) == ["Example Church D"]


def test_safe_002_rename_to_the_same_name_writes_nothing(conn, admin_id):
    church_id = add_church(conn, "Example Church D", admin_id)
    assert rename_church(conn, church_id, " Example Church D ", admin_id) is False
    assert [r[2] for r in _audit_rows(conn)] == ["church_add"]


def test_safe_002_rename_refuses_another_churchs_name(conn, admin_id):
    load(conn, ["Example Church A"])
    church_id = add_church(conn, "Example Church D", admin_id)
    with pytest.raises(ChurchListError, match="already in the list"):
        rename_church(conn, church_id, "EXAMPLE CHURCH A", admin_id)
    assert _names(conn) == ["Example Church A", "Example Church D"]


def test_safe_002_renaming_a_missing_church_is_not_found(conn, admin_id):
    with pytest.raises(ChurchNotFound):
        rename_church(conn, 999, "Example Church D", admin_id)
