"""End-to-end test for deploy/install.sh in a sandboxed HOME."""
from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "deploy" / "install.sh"


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    fake = tmp_path / "fake-home"
    (fake / "Library" / "Application Support").mkdir(parents=True)
    (fake / "Library" / "LaunchAgents").mkdir(parents=True)
    return fake


def _run_install(fake_home: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "HOME": str(fake_home),
        "INTERCEDER_SKIP_LAUNCHD": "1",
        "INTERCEDER_SKIP_KEYCHAIN": "1",
        "INTERCEDER_SKIP_PREREQ_CHECKS": "1",
    }
    return subprocess.run(
        ["bash", str(INSTALL_SH)],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_install_creates_directory_tree(fake_home: Path) -> None:
    result = _run_install(fake_home)
    assert result.returncode == 0, (
        f"install.sh failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    home = fake_home / "Library" / "Application Support" / "Interceder"
    for sub in (
        "db",
        "blobs",
        "claude-config",
        "claude-config/skills",
        "claude-config/agents",
        "claude-config/plugins",
        "workers",
        "logs",
    ):
        assert (home / sub).is_dir(), f"missing {sub}"
    assert (home / "config.toml").exists()


def test_install_bootstraps_memory_db(fake_home: Path) -> None:
    result = _run_install(fake_home)
    assert result.returncode == 0
    home = fake_home / "Library" / "Application Support" / "Interceder"
    db_file = home / "db" / "memory.sqlite"
    assert db_file.exists()

    conn = sqlite3.connect(db_file)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"schema_meta", "inbox", "outbox"}.issubset(tables)
        version = conn.execute(
            "SELECT MAX(version) FROM schema_meta"
        ).fetchone()[0]
        assert version == 6
    finally:
        conn.close()


def test_install_seeds_claude_config(fake_home: Path) -> None:
    result = _run_install(fake_home)
    assert result.returncode == 0
    home = fake_home / "Library" / "Application Support" / "Interceder"
    settings = home / "claude-config" / "settings.json"
    assert settings.exists()
    assert "interceder" in settings.read_text().lower()

    skills_git = home / "claude-config" / "skills" / ".git"
    assert skills_git.is_dir(), "skills/ must be a git repo"


def test_install_is_idempotent(fake_home: Path) -> None:
    first = _run_install(fake_home)
    assert first.returncode == 0, first.stderr
    second = _run_install(fake_home)
    assert second.returncode == 0, second.stderr
