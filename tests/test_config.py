"""Tests for interceder.config — paths, model IDs, and service defaults."""
from __future__ import annotations

from pathlib import Path

import pytest

from interceder import config


def test_interceder_home_env_override(tmp_interceder_home: Path) -> None:
    """INTERCEDER_HOME env var takes precedence over the default path."""
    assert config.interceder_home() == tmp_interceder_home


def test_interceder_home_default_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With env unset, home defaults to ~/Library/Application Support/Interceder."""
    monkeypatch.delenv("INTERCEDER_HOME", raising=False)
    expected = Path("~/Library/Application Support/Interceder").expanduser()
    assert config.interceder_home() == expected


def test_paths_are_derived_from_home(tmp_interceder_home: Path) -> None:
    """DB, blobs, claude-config, workers, logs all live under home."""
    home = tmp_interceder_home
    assert config.db_path() == home / "db" / "memory.sqlite"
    assert config.blobs_dir() == home / "blobs"
    assert config.claude_config_dir() == home / "claude-config"
    assert config.workers_dir() == home / "workers"
    assert config.logs_dir() == home / "logs"
    assert config.config_toml_path() == home / "config.toml"


def test_migrations_dir_is_packaged(tmp_interceder_home: Path) -> None:
    """The migrations directory ships inside the package."""
    mig = config.migrations_dir()
    assert mig.is_dir()
    assert mig.name == "migrations"
    assert mig.parent.name == "interceder"


def test_model_ids_are_defined() -> None:
    """Every model ID referenced by the spec lives in one module (N18)."""
    assert config.MANAGER_MODEL == "claude-opus-4-6"
    assert config.WORKER_DEFAULT_MODEL == "claude-sonnet-4-6"
    assert config.CLASSIFIER_MODEL == "claude-haiku-4-5-20251001"


def test_gateway_bind_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gateway bind host/port have sane defaults and are env-overridable."""
    monkeypatch.delenv("INTERCEDER_GATEWAY_HOST", raising=False)
    monkeypatch.delenv("INTERCEDER_GATEWAY_PORT", raising=False)
    assert config.gateway_bind_host() == "127.0.0.1"
    assert config.gateway_bind_port() == 7878

    monkeypatch.setenv("INTERCEDER_GATEWAY_HOST", "100.64.1.2")
    monkeypatch.setenv("INTERCEDER_GATEWAY_PORT", "9999")
    assert config.gateway_bind_host() == "100.64.1.2"
    assert config.gateway_bind_port() == 9999
