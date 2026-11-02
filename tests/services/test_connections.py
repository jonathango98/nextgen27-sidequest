import re
import threading

import pytest

from app.config import load_config
from app.db import connect
from app.services import connections, qr
from app.services.connections import ScanRefused
from app.services.game_state import GameNotOn, set_state
from tests.conftest import seed_fake_players

# Fake data (ENG-047), never a real key (SAFE-030).
FAKE_KEY = "test-only-fake-signing-key"
FAKE_NOW = 1_800_000_000.0  # fixed clock, not a game number
CONFIG = load_config()
QR = CONFIG["qr"]
PLAYERS = ("testpid01", "testpid02", "testpid03")


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    monkeypatch.setenv(qr.KEY_ENV, FAKE_KEY)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "side-quest.db"


@pytest.fixture
def ids(db_path):
    return seed_fake_players(db_path, *PLAYERS)


@pytest.fixture
def conn(db_path, ids):
    conn = connect(db_path)
    yield conn
    conn.close()


def _code_of(public_id, now=FAKE_NOW):
    return qr.payload(qr.PLAYER_KIND, public_id, now, QR)


def _scan(conn, scanner="testpid01", scanned="testpid02", **overrides):
    args = {
        "scanner_public_id": scanner,
        "payload": _code_of(scanned),
        "now": FAKE_NOW,
        "config": CONFIG,
    }
    return connections.scan(conn, **{**args, **overrides})


def _rows(conn):
    return conn.execute("SELECT * FROM connection").fetchall()


def _refused(call) -> ScanRefused:
    with pytest.raises(ScanRefused) as refused:
        call()
    return refused.value


def test_game_014_scan_saves_the_pair(conn, ids):
    met = _scan(conn)
    (row,) = _rows(conn)
    assert row["id"] == met.id
    assert row["scanner_id"] == ids["testpid01"]
    # SAFE-004: the scanner sees first name and church only.
    assert (met.other_first_name, met.other_church) == ("Test", "Example Church A")


def test_game_013_pair_is_saved_low_id_first(conn, ids):
    _scan(conn, scanner="testpid02", scanned="testpid01")
    (row,) = _rows(conn)
    low, high = sorted((ids["testpid01"], ids["testpid02"]))
    assert (row["player_low_id"], row["player_high_id"]) == (low, high)
    assert row["scanner_id"] == ids["testpid02"]


@pytest.mark.parametrize(
    "scanner, scanned", [("testpid01", "testpid02"), ("testpid02", "testpid01")]
)
def test_game_013_same_pair_counts_once(conn, scanner, scanned):
    _scan(conn)
    refused = _refused(lambda: _scan(conn, scanner=scanner, scanned=scanned))
    assert (refused.status, refused.code) == (409, "ALREADY_CONNECTED")
    assert len(_rows(conn)) == 1


def test_game_013_two_phones_scanning_each_other_at_once_save_one_pair(db_path, conn):
    start = threading.Barrier(2)
    results = []

    def scan(scanner, scanned):
        own = connect(db_path)
        try:
            start.wait()
            results.append(_scan(own, scanner=scanner, scanned=scanned).id)
        except ScanRefused as refused:
            results.append(refused.code)
        finally:
            own.close()

    threads = [
        threading.Thread(target=scan, args=("testpid01", "testpid02")),
        threading.Thread(target=scan, args=("testpid02", "testpid01")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ALREADY_CONNECTED") == 1
    assert len(_rows(conn)) == 1


def test_game_014_cannot_scan_yourself(conn):
    refused = _refused(lambda: _scan(conn, scanned="testpid01"))
    assert (refused.status, refused.code) == (400, "BAD_INPUT")
    assert refused.message == "That's your own code! Scan a friend's."
    assert _rows(conn) == []


def test_arch_022_code_from_previous_window_is_accepted(conn):
    earlier = FAKE_NOW - QR["rotation_seconds"] * QR["accepted_previous_steps"]
    _scan(conn, payload=_code_of("testpid02", earlier))
    assert len(_rows(conn)) == 1


def test_arch_022_old_code_is_refused_as_expired(conn):
    too_old = FAKE_NOW - QR["rotation_seconds"] * (QR["accepted_previous_steps"] + 1)
    refused = _refused(lambda: _scan(conn, payload=_code_of("testpid02", too_old)))
    assert (refused.status, refused.code) == (410, "CODE_EXPIRED")
    assert _rows(conn) == []


def test_arch_026_made_up_code_is_refused(conn):
    # A valid-looking code that is one off from the real one.
    head, real = _code_of("testpid02").rsplit(".", 1)
    wrong = str((int(real) + 1) % 10 ** QR["code_digits"]).zfill(QR["code_digits"])
    refused = _refused(lambda: _scan(conn, payload=f"{head}.{wrong}"))
    assert refused.code == "CODE_EXPIRED"
    assert _rows(conn) == []


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "https://example.com/menu",
        "SQ0.P.testpid02.123456",
        "{fmt}.S.testsession.123456",  # check-in codes come with the check-in pieces
        "{fmt}.P..123456",
        "{fmt}.P.testpid02",
        "{fmt}.P.testpid02.123456.extra",
    ],
)
def test_arch_025_other_payloads_are_not_a_code(conn, payload):
    refused = _refused(
        lambda: _scan(conn, payload=payload.format(fmt=QR["format_version"]))
    )
    assert (refused.status, refused.code) == (400, "NOT_A_CODE")
    assert _rows(conn) == []


def test_api_005_code_for_unknown_player_is_not_found(conn):
    refused = _refused(lambda: _scan(conn, scanned="testpid99"))
    assert (refused.status, refused.code) == (404, "NOT_FOUND")


@pytest.mark.parametrize(("state", "code"), [("paused", "PAUSED"), ("off", "GAME_OFF")])
def test_game_102_game_108_scan_refused_unless_game_is_on(conn, state, code):
    set_state(conn, state)
    with pytest.raises(GameNotOn) as refused:
        _scan(conn)
    assert refused.value.error_code == code
    assert _rows(conn) == []


def test_game_018_same_church_is_saved(conn, db_path):
    conn.execute("INSERT INTO church (name) VALUES ('Example Church B')")
    conn.execute(
        "UPDATE player SET church_id = (SELECT id FROM church WHERE name = 'Example Church B')"
        " WHERE public_id = 'testpid03'"
    )
    _scan(conn)
    _scan(conn, scanned="testpid03")
    same = [
        row["is_same_church"]
        for row in conn.execute("SELECT * FROM connection ORDER BY id")
    ]
    assert same == [1, 0]


def test_game_019_every_category_in_config_has_a_question():
    assert set(CONFIG["icebreaker"]["categories"]) <= set(connections.QUESTIONS)


def test_game_019_question_is_picked_from_config_pool(conn, monkeypatch):
    picked = []
    monkeypatch.setattr(
        connections.random, "choice", lambda pool: picked.append(list(pool)) or pool[-1]
    )
    met = _scan(conn)
    assert picked == [CONFIG["icebreaker"]["categories"]]
    category = CONFIG["icebreaker"]["categories"][-1]
    assert _rows(conn)[0]["question_category"] == category
    assert met.question == connections.QUESTIONS[category]


def test_game_017_both_players_see_the_same_question(conn, ids):
    met = _scan(conn)
    theirs = connections.for_player(conn, met.id, ids["testpid02"])
    assert theirs.question == met.question
    assert theirs.id == met.id


def test_safe_006_someone_outside_the_pair_sees_nothing(conn, ids):
    met = _scan(conn)
    assert connections.for_player(conn, met.id, ids["testpid03"]) is None


def test_safe_043_questions_never_ask_for_contact_or_where_you_stay():
    banned = re.compile(
        r"phone|number|email|instagram|social|handle|room|hotel|stay|address",
        re.IGNORECASE,
    )
    assert not [q for q in connections.QUESTIONS.values() if banned.search(q)]


def test_api_032_incoming_lists_only_scans_by_someone_else(conn, ids):
    me = ids["testpid02"]
    start = connections.latest_id(conn, me)
    first = _scan(conn)  # testpid01 scans me
    _scan(conn, scanner="testpid02", scanned="testpid03")  # I scan someone
    notes = connections.incoming(conn, me, start)
    assert [n.id for n in notes] == [first.id]
    assert connections.incoming(conn, me, connections.latest_id(conn, me)) == []
