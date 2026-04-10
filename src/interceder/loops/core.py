"""KarpathyLoop core — shared infrastructure for L1/L2/L3 loops.

All three loop layers are specializations of this core:
- Single editable asset
- Scalar metric (higher or lower is better)
- Time-boxed iterations
- Keep-or-discard based on metric improvement
- All iterations committed to git
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("interceder.loops.core")


@dataclass
class LoopConfig:
    layer: str  # L1 | L2 | L3
    editable_asset: str
    metric_name: str
    higher_is_better: bool = True
    keep_threshold: float = 0.0
    branch: str = ""
    worktree: str | None = None
    max_iterations: int = 100
    time_budget_seconds: int = 3600
    cost_budget_usd: float | None = None


@dataclass
class LoopResult:
    loop_id: str
    iterations_run: int
    best_score: float | None
    status: str  # done | budget_exhausted | paused | failed


class KarpathyLoop:
    def __init__(
        self,
        *,
        config: LoopConfig,
        conn: sqlite3.Connection,
    ) -> None:
        self._config = config
        self._conn = conn
        self._loop_id = f"loop-{uuid.uuid4().hex[:12]}"
        self._started_at = time.time()
        self._iterations_run = 0
        self._best_score: float | None = None
        self._paused = False

        # Register in DB
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO karpathy_loops
                (id, layer, editable_asset, metric_name, metric_definition_json,
                 branch, worktree, status, budget_json, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            """,
            (
                self._loop_id, config.layer, config.editable_asset,
                config.metric_name, "{}",
                config.branch, config.worktree,
                json.dumps({
                    "max_iterations": config.max_iterations,
                    "time_budget_seconds": config.time_budget_seconds,
                }),
                now,
            ),
        )

    @property
    def loop_id(self) -> str:
        return self._loop_id

    def should_keep(
        self,
        candidate_score: float,
        current_best: float | None = None,
    ) -> bool:
        """Decide whether to keep a candidate edit based on metric improvement."""
        best = current_best if current_best is not None else self._best_score

        if best is None:
            return True  # First iteration — always keep

        if self._config.higher_is_better:
            improvement = candidate_score - best
        else:
            improvement = best - candidate_score

        return improvement >= self._config.keep_threshold

    def budget_exhausted(self) -> bool:
        elapsed = time.time() - self._started_at
        if elapsed >= self._config.time_budget_seconds:
            return True
        if self._iterations_run >= self._config.max_iterations:
            return True
        return False

    def record_iteration(
        self,
        *,
        commit_hash: str,
        metric_value: float,
        kept: bool,
        rationale: str,
        wall_seconds: int,
    ) -> None:
        now = int(time.time())
        self._iterations_run += 1

        if kept:
            self._best_score = metric_value

        self._conn.execute(
            """
            INSERT INTO karpathy_iterations
                (loop_id, iteration, commit_hash, metric_value, kept, rationale, wall_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._loop_id, self._iterations_run, commit_hash,
                metric_value, 1 if kept else 0, rationale, wall_seconds, now,
            ),
        )

        # Update loop state
        self._conn.execute(
            """
            UPDATE karpathy_loops
            SET iterations=?, best_score=?
            WHERE id=?
            """,
            (self._iterations_run, self._best_score, self._loop_id),
        )

    def pause(self) -> None:
        self._paused = True
        self._conn.execute(
            "UPDATE karpathy_loops SET status='paused' WHERE id=?",
            (self._loop_id,),
        )

    def complete(self, status: str = "done") -> LoopResult:
        now = int(time.time())
        self._conn.execute(
            "UPDATE karpathy_loops SET status=?, ended_at=? WHERE id=?",
            (status, now, self._loop_id),
        )
        return LoopResult(
            loop_id=self._loop_id,
            iterations_run=self._iterations_run,
            best_score=self._best_score,
            status=status,
        )
