import pytest
import yaml

from app.config import SUPPORTED_CONFIG_VERSION, ConfigError, load_config


def test_eng_031_config_loads_game_config():
    config = load_config()
    for section in ("game", "points", "limits", "qr", "auth", "features", "ui"):
        assert section in config


def test_arch_004_config_rejects_unsafe_yaml(tmp_path):
    path = tmp_path / "game-config.yaml"
    path.write_text(
        f"config_version: {SUPPORTED_CONFIG_VERSION}\n"
        "boom: !!python/object/apply:os.getcwd []\n"
    )
    with pytest.raises(yaml.YAMLError):
        load_config(path)


def test_eng_030_config_version_mismatch_fails(tmp_path):
    path = tmp_path / "game-config.yaml"
    path.write_text(f"config_version: {SUPPORTED_CONFIG_VERSION + 1}\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_eng_030_config_must_be_a_map(tmp_path):
    path = tmp_path / "game-config.yaml"
    path.write_text("- just\n- a list\n")
    with pytest.raises(ConfigError):
        load_config(path)
