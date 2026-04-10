"""Tests for the proactive message engine."""
from __future__ import annotations

import time

from interceder.manager.proactive import ProactiveEngine


def test_should_send_respects_rate_limit() -> None:
    engine = ProactiveEngine(rate_limits={"worker_done": 30})
    assert engine.should_send("worker_done") is True
    engine.record_sent("worker_done")
    assert engine.should_send("worker_done") is False


def test_should_send_after_cooldown() -> None:
    engine = ProactiveEngine(rate_limits={"worker_done": 0})
    engine.record_sent("worker_done")
    assert engine.should_send("worker_done") is True  # 0 = no cooldown


def test_quiet_hours_suppresses() -> None:
    engine = ProactiveEngine(
        rate_limits={},
        quiet_start_hour=0,
        quiet_end_hour=24,  # always quiet
    )
    assert engine.is_quiet_hours() is True
    assert engine.should_send("idle_reflection", urgent=False) is False


def test_urgent_bypasses_quiet_hours() -> None:
    engine = ProactiveEngine(
        rate_limits={},
        quiet_start_hour=0,
        quiet_end_hour=24,
    )
    assert engine.should_send("failure", urgent=True) is True
