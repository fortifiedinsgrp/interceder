"""End-to-end tests for deploy/update.sh in a sandboxed HOME."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATE_SH = REPO_ROOT / "deploy" / "update.sh"


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    fake = tmp_path / "fake-home"
    (fake / "Library" / "Application Support").mkdir(parents=True)
    (fake / "Library" / "LaunchAgents").mkdir(parents=True)
    return fake


def _run_update(fake_home: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "HOME": str(fake_home),
        "INTERCEDER_SKIP_LAUNCHD": "1",
        "INTERCEDER_SKIP_WEBAPP": "1",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(UPDATE_SH)],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_update_script_exists() -> None:
    assert UPDATE_SH.exists(), "deploy/update.sh does not exist"


def test_update_runs_and_exits_zero(fake_home: Path) -> None:
    result = _run_update(fake_home)
    assert result.returncode == 0, (
        f"update.sh failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_update_logs_steps(fake_home: Path) -> None:
    result = _run_update(fake_home)
    assert result.returncode == 0
    assert "pulling latest code" in result.stdout
    assert "syncing Python dependencies" in result.stdout
    assert "update complete" in result.stdout


def test_update_is_idempotent(fake_home: Path) -> None:
    first = _run_update(fake_home)
    assert first.returncode == 0, first.stderr
    second = _run_update(fake_home)
    assert second.returncode == 0, second.stderr
