"""Loads game numbers from foundation/game-config.yaml (ENG-030, ENG-031)."""

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "foundation" / "game-config.yaml"

# The shape of the config file this code understands, not a game number (ENG-030).
SUPPORTED_CONFIG_VERSION = 1


class ConfigError(Exception):
    pass


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)  # ARCH-004: safe_load only
    if not isinstance(data, dict):
        raise ConfigError(f"{path} is not a YAML map")
    version = data.get("config_version")
    if version != SUPPORTED_CONFIG_VERSION:
        raise ConfigError(
            f"{path} has config_version {version!r}, "
            f"this code supports {SUPPORTED_CONFIG_VERSION}"
        )
    return data
