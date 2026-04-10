"""Tests for the global and per-workflow kill switches."""
from __future__ import annotations

from interceder.manager.kill_switch import KillSwitch


def test_global_kill() -> None:
    ks = KillSwitch()
    assert ks.is_killed() is False
    ks.kill_all(reason="user requested stop")
    assert ks.is_killed() is True
    assert "user requested" in ks.kill_reason()


def test_resume_after_kill() -> None:
    ks = KillSwitch()
    ks.kill_all(reason="test")
    ks.resume()
    assert ks.is_killed() is False


def test_per_workflow_kill() -> None:
    ks = KillSwitch()
    ks.kill_workflow("loop-123", reason="budget exceeded")
    assert ks.is_workflow_killed("loop-123") is True
    assert ks.is_workflow_killed("loop-456") is False
