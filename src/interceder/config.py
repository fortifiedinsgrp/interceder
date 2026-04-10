"""Central configuration: paths, model IDs, service defaults.

N18: all Claude/model IDs live in this module so upgrades are one-line
changes. All path and env var lookups are functions (not module-level
constants) so tests can monkeypatch the environment freely.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# ----------------------------------------------------------------------
# Model IDs — single source of truth
# ----------------------------------------------------------------------
MANAGER_MODEL: Final[str] = "claude-opus-4-6"
WORKER_DEFAULT_MODEL: Final[str] = "claude-sonnet-4-6"
CLASSIFIER_MODEL: Final[str] = "claude-haiku-4-5-20251001"


# ----------------------------------------------------------------------
# Filesystem paths
# ----------------------------------------------------------------------
_DEFAULT_HOME = Path("~/Library/Application Support/Interceder").expanduser()


def interceder_home() -> Path:
    """Return the Interceder home directory.

    Honors the INTERCEDER_HOME env var so tests can isolate into tmp dirs.
    """
    override = os.environ.get("INTERCEDER_HOME")
    if override:
        return Path(override).expanduser()
    return _DEFAULT_HOME


def db_path() -> Path:
    return interceder_home() / "db" / "memory.sqlite"


def blobs_dir() -> Path:
    return interceder_home() / "blobs"


def claude_config_dir() -> Path:
    return interceder_home() / "claude-config"


def workers_dir() -> Path:
    return interceder_home() / "workers"


def logs_dir() -> Path:
    return interceder_home() / "logs"


def config_toml_path() -> Path:
    return interceder_home() / "config.toml"


def migrations_dir() -> Path:
    """Path to the packaged SQL migrations directory."""
    return Path(__file__).parent / "migrations"


# ----------------------------------------------------------------------
# Gateway bind defaults (overridable via env for tests and launchd)
# ----------------------------------------------------------------------
def gateway_bind_host() -> str:
    return os.environ.get("INTERCEDER_GATEWAY_HOST", "127.0.0.1")


def gateway_bind_port() -> int:
    return int(os.environ.get("INTERCEDER_GATEWAY_PORT", "7878"))
