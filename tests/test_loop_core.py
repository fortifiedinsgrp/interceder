"""Tests for the KarpathyLoop core — keep/discard logic, budget enforcement."""
from __future__ import annotations

import time
from pathlib import Path

from interceder import config
from interceder.loops.core import KarpathyLoop, LoopConfig, LoopResult
from interceder.memory import db, runner


def _setup(tmp_interceder_home: Path) -> None:
    runner.migrate()


def test_loop_keeps_improvement(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())

    loop_config = LoopConfig(
        layer="L2",
        editable_asset="/tmp/test_skill.md",
        metric_name="success_rate",
        higher_is_better=True,
        keep_threshold=0.0,
        branch="test-l2",
        max_iterations=3,
        time_budget_seconds=60,
    )
    loop = KarpathyLoop(config=loop_config, conn=conn)
    # Simulate an iteration with improvement
    kept = loop.should_keep(candidate_score=0.8, current_best=0.5)
    assert kept is True


def test_loop_discards_regression(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())

    loop_config = LoopConfig(
        layer="L2",
        editable_asset="/tmp/test_skill.md",
        metric_name="success_rate",
        higher_is_better=True,
        keep_threshold=0.0,
        branch="test-l2",
        max_iterations=3,
        time_budget_seconds=60,
    )
    loop = KarpathyLoop(config=loop_config, conn=conn)
    kept = loop.should_keep(candidate_score=0.3, current_best=0.5)
    assert kept is False


def test_loop_respects_budget(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())

    loop_config = LoopConfig(
        layer="L2",
        editable_asset="/tmp/test_skill.md",
        metric_name="success_rate",
        higher_is_better=True,
        keep_threshold=0.0,
        branch="test-l2",
        max_iterations=2,
        time_budget_seconds=0,  # immediately exhausted
    )
    loop = KarpathyLoop(config=loop_config, conn=conn)
    assert loop.budget_exhausted() is True
