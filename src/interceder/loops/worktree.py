"""Git worktree management for Karpathy loop isolation."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("interceder.loops.worktree")


def create_worktree(
    *,
    repo_path: Path,
    branch: str,
    worktree_root: Path,
) -> Path:
    """Create a git worktree for an isolated loop iteration."""
    worktree_root.mkdir(parents=True, exist_ok=True)
    wt_path = worktree_root / branch

    # Create a new branch from HEAD
    subprocess.run(
        ["git", "branch", branch, "HEAD"],
        cwd=repo_path,
        capture_output=True,
        check=False,  # OK if branch already exists
    )

    subprocess.run(
        ["git", "worktree", "add", str(wt_path), branch],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    log.info("created worktree at %s on branch %s", wt_path, branch)
    return wt_path


def cleanup_worktree(*, repo_path: Path, worktree_path: Path) -> None:
    """Remove a git worktree and its branch."""
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path), "--force"],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    if worktree_path.exists():
        shutil.rmtree(worktree_path)
    log.info("cleaned up worktree %s", worktree_path)
