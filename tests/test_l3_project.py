"""Tests for L3 Project Loop — Karpathy-style optimization."""
from __future__ import annotations

import subprocess
from pathlib import Path

from interceder.loops.l3_project import L3ProjectLoop


def _init_repo(path: Path) -> Path:
    """Create a minimal git repo for testing."""
    repo = path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    (repo / "model.py").write_text("accuracy = 0.85\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@test", "-c", "user.name=Test",
         "commit", "-m", "init"],
        cwd=repo, capture_output=True, check=True,
    )
    return repo


def test_l3_loop_init(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    loop = L3ProjectLoop(
        repo_path=repo,
        editable_file="model.py",
        metric_command="echo 0.85",
        branch="loop-test",
        worktree_root=tmp_path / "worktrees",
        conn=None,
    )
    assert loop._editable_file == "model.py"
    assert loop._max_iterations == 100


def test_l3_loop_start_creates_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    loop = L3ProjectLoop(
        repo_path=repo,
        editable_file="model.py",
        metric_command="echo 0.85",
        branch="loop-start-test",
        worktree_root=tmp_path / "worktrees",
        conn=None,
    )
    wt_path = loop.start()
    assert Path(wt_path).is_dir()
    assert (Path(wt_path) / "model.py").exists()
