"""L3 Project Loop — Karpathy-style optimization on a single file.

The user specifies:
- A file in a repo
- A scalar metric (shell command)
- A time/cost budget

The loop runs in an isolated git worktree, generates candidate edits,
evaluates them against the metric, and keeps improvements.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from interceder.loops.core import KarpathyLoop, LoopConfig, LoopResult

log = logging.getLogger("interceder.loops.l3_project")


class L3ProjectLoop:
    """Orchestrates a Karpathy L3 loop on a user-specified project file."""

    def __init__(
        self,
        *,
        repo_path: Path,
        editable_file: str,
        metric_command: str,
        branch: str,
        worktree_root: Path,
        conn: object,
        max_iterations: int = 100,
        time_budget_seconds: int = 7200,
    ) -> None:
        self._repo_path = repo_path
        self._editable_file = editable_file
        self._metric_command = metric_command
        self._branch = branch
        self._worktree_root = worktree_root
        self._conn = conn
        self._max_iterations = max_iterations
        self._time_budget = time_budget_seconds

    def start(self) -> str:
        """Initialize the loop. Returns the loop ID."""
        from interceder.loops.worktree import create_worktree

        # Create isolated worktree
        wt_path = create_worktree(
            repo_path=self._repo_path,
            branch=self._branch,
            worktree_root=self._worktree_root,
        )

        log.info(
            "L3 loop started: file=%s, metric=%s, worktree=%s",
            self._editable_file, self._metric_command, wt_path,
        )
        return str(wt_path)
