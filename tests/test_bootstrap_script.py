"""Tests for deploy/bootstrap.sh — validates the thin curl-able bootstrap."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SH = REPO_ROOT / "deploy" / "bootstrap.sh"


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A temp directory to use as clone target."""
    return tmp_path / "clone-target"


def _run_bootstrap(
    sandbox: Path,
    *,
    skip_launch: bool = True,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "INTERCEDER_CLONE_DIR": str(sandbox),
        # Always skip launching claude in tests
        "INTERCEDER_SKIP_LAUNCH": "1" if skip_launch else "0",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(BOOTSTRAP_SH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_bootstrap_script_exists() -> None:
    assert BOOTSTRAP_SH.exists()
    assert BOOTSTRAP_SH.stat().st_mode & 0o111, "bootstrap.sh must be executable"


def test_bootstrap_clones_repo(sandbox: Path) -> None:
    result = _run_bootstrap(sandbox)
    assert result.returncode == 0, (
        f"bootstrap.sh failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert (sandbox / ".git").is_dir(), "repo should be cloned"
    assert (sandbox / "pyproject.toml").exists(), "repo contents should exist"


def test_bootstrap_pulls_if_already_cloned(sandbox: Path) -> None:
    # First run clones
    first = _run_bootstrap(sandbox)
    assert first.returncode == 0, first.stderr
    # Second run should pull, not fail
    second = _run_bootstrap(sandbox)
    assert second.returncode == 0, second.stderr
    assert "already exists" in second.stdout.lower() or "pulling" in second.stdout.lower()


def test_bootstrap_clones_without_claude(sandbox: Path, tmp_path: Path) -> None:
    """When claude is missing, bootstrap should still clone and exit 0 with a warning."""
    # Build a PATH that has git but NOT claude
    bin_dir = tmp_path / "bin-no-claude"
    bin_dir.mkdir()
    git_real = Path("/usr/bin/git")
    if not git_real.exists():
        git_real = Path("/opt/homebrew/bin/git")
    (bin_dir / "git").symlink_to(git_real)
    bash_path = Path("/bin/bash")
    if bash_path.exists():
        (bin_dir / "bash").symlink_to(bash_path)

    result = _run_bootstrap(
        sandbox,
        skip_launch=False,
        extra_env={"PATH": str(bin_dir)},
    )
    assert result.returncode == 0, (
        f"expected exit 0\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert (sandbox / ".git").is_dir(), "repo should be cloned even without claude"
    assert "claude" in result.stdout.lower(), "output should mention claude"


def test_bootstrap_fails_without_git(sandbox: Path, tmp_path: Path) -> None:
    # Create a bin dir that has bash but not git or claude
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    # Symlink bash so the script can execute
    bash_path = Path("/bin/bash")
    if bash_path.exists():
        (empty_bin / "bash").symlink_to(bash_path)
    # PATH contains only the empty dir — no git, no claude
    result = _run_bootstrap(sandbox, extra_env={"PATH": str(empty_bin)})
    assert result.returncode != 0
    assert "git" in result.stderr.lower() or "git" in result.stdout.lower()
