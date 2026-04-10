"""Tests for L1 User-Model Loop — prompt evolution with guardrails."""
from __future__ import annotations

from pathlib import Path

from interceder.loops.l1_user_model import L1UserModelLoop, EDITABLE_FILE


def test_editable_file_constant() -> None:
    assert EDITABLE_FILE == "src/interceder/manager/prompt.py"


def test_starts_disabled() -> None:
    loop = L1UserModelLoop(repo_path=Path("/tmp/fake"), conn=None)
    assert loop.is_enabled is False


def test_enable() -> None:
    loop = L1UserModelLoop(repo_path=Path("/tmp/fake"), conn=None)
    loop.enable()
    assert loop.is_enabled is True


def test_requires_restart() -> None:
    loop = L1UserModelLoop(repo_path=Path("/tmp/fake"), conn=None)
    assert loop.requires_restart() is True


def test_config_wiring() -> None:
    loop = L1UserModelLoop(
        repo_path=Path("/tmp/fake"),
        conn=None,
        max_iterations=10,
        time_budget_seconds=1800,
    )
    assert loop._config.layer == "L1"
    assert loop._config.editable_asset == EDITABLE_FILE
    assert loop._config.branch == "self-mod/l1-prompt"
    assert loop._config.metric_name == "user_satisfaction"
    assert loop._config.higher_is_better is True
    assert loop._config.max_iterations == 10
    assert loop._config.time_budget_seconds == 1800
