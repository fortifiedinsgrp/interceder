"""Shared pytest fixtures for Interceder tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_interceder_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate tests into a temporary INTERCEDER_HOME."""
    home = tmp_path / "interceder-home"
    home.mkdir()
    monkeypatch.setenv("INTERCEDER_HOME", str(home))
    return home
