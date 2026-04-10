"""Tests for git worktree management for Karpathy loops."""
from __future__ import annotations

import subprocess
from pathlib import Path

from interceder.loops.worktree import create_worktree, cleanup_worktree


def _init_repo(path: Path) -> Path:
    """Create a minimal git repo for testing."""
    repo = path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    (repo / "file.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@test", "-c", "user.name=Test",
         "commit", "-m", "init"],
        cwd=repo, capture_output=True, check=True,
    )
    return repo


def test_create_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt_path = create_worktree(
        repo_path=repo,
        branch="loop-test",
        worktree_root=tmp_path / "worktrees",
    )
    assert wt_path.is_dir()
    assert (wt_path / "file.py").exists()


def test_cleanup_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt_path = create_worktree(
        repo_path=repo,
        branch="loop-cleanup",
        worktree_root=tmp_path / "worktrees",
    )
    cleanup_worktree(repo_path=repo, worktree_path=wt_path)
    assert not wt_path.exists()
