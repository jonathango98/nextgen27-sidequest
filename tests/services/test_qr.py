import pytest

from app.config import load_config
from app.services import qr

# Fake data (ENG-047), never a real key (SAFE-030).
FAKE_KEY = "test-only-fake-signing-key"
OTHER_FAKE_KEY = "test-only-other-fake-key"
PLAYER = "testpid01"  # fake public_id
OTHER_PLAYER = "testpid02"
FAKE_NOW = 1_800_000_000.0  # fixed clock, not a game number


@pytest.fixture
def cfg():
    return load_config()["qr"]


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    monkeypatch.setenv(qr.KEY_ENV, FAKE_KEY)


def window_start(cfg):
    rotation = cfg["rotation_seconds"]
    return FAKE_NOW // rotation * rotation


def code_at(now, cfg, public_id=PLAYER):
    return qr.payload(qr.PLAYER_KIND, public_id, now, cfg).rsplit(".", 1)[1]


def test_arch_020_payload_format(cfg):
    parts = qr.payload(qr.PLAYER_KIND, PLAYER, FAKE_NOW, cfg).split(".")
    assert parts[:3] == [cfg["format_version"], "P", PLAYER]
    assert len(parts) == 4


def test_arch_021_code_has_config_digits(cfg):
    code = code_at(FAKE_NOW, cfg)
    assert code.isdigit()
    assert len(code) == cfg["code_digits"]


def test_game_001_code_stays_the_same_within_a_window(cfg):
    start = window_start(cfg)
    assert code_at(start, cfg) == code_at(start + cfg["rotation_seconds"] - 1, cfg)


def test_game_001_code_changes_each_window(cfg):
    start = window_start(cfg)
    assert code_at(start, cfg) != code_at(start + cfg["rotation_seconds"], cfg)


def test_arch_022_current_code_accepted(cfg):
    code = code_at(FAKE_NOW, cfg)
    assert qr.verify(qr.PLAYER_KIND, PLAYER, code, FAKE_NOW, cfg)


def test_arch_022_previous_window_accepted(cfg):
    start = window_start(cfg)
    code = code_at(start, cfg)
    later = start + cfg["rotation_seconds"] * cfg["accepted_previous_steps"]
    assert qr.verify(qr.PLAYER_KIND, PLAYER, code, later, cfg)


def test_arch_022_older_code_refused(cfg):
    start = window_start(cfg)
    code = code_at(start, cfg)
    too_late = start + cfg["rotation_seconds"] * (cfg["accepted_previous_steps"] + 1)
    assert not qr.verify(qr.PLAYER_KIND, PLAYER, code, too_late, cfg)


def test_arch_022_future_code_refused(cfg):
    start = window_start(cfg)
    next_code = code_at(start + cfg["rotation_seconds"], cfg)
    assert not qr.verify(qr.PLAYER_KIND, PLAYER, next_code, start, cfg)


@pytest.mark.parametrize("bad", ["", "12345a", "١٢٣٤٥٦", "1" * 20])
def test_arch_022_malformed_code_refused(cfg, bad):
    assert not qr.verify(qr.PLAYER_KIND, PLAYER, bad, FAKE_NOW, cfg)


def test_arch_023_each_player_gets_own_code(cfg):
    assert code_at(FAKE_NOW, cfg) != code_at(FAKE_NOW, cfg, public_id=OTHER_PLAYER)


def test_arch_023_code_depends_on_server_key(cfg, monkeypatch):
    code = code_at(FAKE_NOW, cfg)
    monkeypatch.setenv(qr.KEY_ENV, OTHER_FAKE_KEY)
    assert code_at(FAKE_NOW, cfg) != code
    assert not qr.verify(qr.PLAYER_KIND, PLAYER, code, FAKE_NOW, cfg)


@pytest.mark.parametrize("value", [None, ""])
def test_arch_023_missing_key_refuses(cfg, monkeypatch, value):
    if value is None:
        monkeypatch.delenv(qr.KEY_ENV)
    else:
        monkeypatch.setenv(qr.KEY_ENV, value)
    with pytest.raises(qr.SigningKeyMissing):
        qr.payload(qr.PLAYER_KIND, PLAYER, FAKE_NOW, cfg)


def test_api_030_seconds_left_counts_down_to_next_window(cfg):
    start = window_start(cfg)
    rotation = cfg["rotation_seconds"]
    assert qr.seconds_left(start, cfg) == rotation
    assert qr.seconds_left(start + 0.5, cfg) == rotation
    assert qr.seconds_left(start + rotation - 0.5, cfg) == 1
