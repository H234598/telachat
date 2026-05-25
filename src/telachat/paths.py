from __future__ import annotations

import os
from pathlib import Path

from .defaults import APP_NAME


def _xdg_path(name: str, fallback: str) -> Path:
    value = os.environ.get(name)
    if value:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
    return Path.home() / fallback


def config_dir() -> Path:
    return _xdg_path("XDG_CONFIG_HOME", ".config") / APP_NAME


def data_dir() -> Path:
    return _xdg_path("XDG_DATA_HOME", ".local/share") / APP_NAME


def state_dir() -> Path:
    return _xdg_path("XDG_STATE_HOME", ".local/state") / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.toml"


def db_path() -> Path:
    return data_dir() / "history.sqlite3"
