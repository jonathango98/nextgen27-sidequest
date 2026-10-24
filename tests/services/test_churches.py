import io

import pytest

from app.db import connect, migrate
from app.services.churches import ChurchListError, load, main, parse

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
