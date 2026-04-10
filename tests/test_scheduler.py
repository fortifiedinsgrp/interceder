"""Tests for the Scheduler — register, tick, list."""
from __future__ import annotations

import time
from pathlib import Path

from interceder import config
from interceder.memory import db, runner
from interceder.scheduler.scheduler import Scheduler


def _setup(tmp_interceder_home: Path) -> Scheduler:
    runner.migrate()
    conn = db.connect(config.db_path())
    return Scheduler(conn)


def test_register_schedule(tmp_interceder_home: Path) -> None:
    sched = _setup(tmp_interceder_home)
    sid = sched.register(
        name="daily-triage",
        cron_expr="0 9 * * 1-5",
        prompt="Triage GitHub issues on dashboard repo",
    )
    assert sid is not None
    schedules = sched.list_schedules()
    assert len(schedules) == 1
    assert schedules[0]["name"] == "daily-triage"


def test_tick_fires_due_schedule(tmp_interceder_home: Path) -> None:
    sched = _setup(tmp_interceder_home)
    sched.register(
        name="overdue-task",
        cron_expr="* * * * *",
        prompt="run this now",
        next_run_at=int(time.time()) - 60,
    )
    fired = sched.tick()
    assert len(fired) == 1
    assert fired[0]["name"] == "overdue-task"


def test_tick_does_not_fire_future_schedule(tmp_interceder_home: Path) -> None:
    sched = _setup(tmp_interceder_home)
    sched.register(
        name="future-task",
        cron_expr="0 9 * * *",
        prompt="not yet",
        next_run_at=int(time.time()) + 3600,
    )
    fired = sched.tick()
    assert len(fired) == 0


def test_disable_schedule(tmp_interceder_home: Path) -> None:
    sched = _setup(tmp_interceder_home)
    sid = sched.register(
        name="disable-me",
        cron_expr="* * * * *",
        prompt="test",
        next_run_at=int(time.time()) - 60,
    )
    sched.set_enabled(sid, False)
    fired = sched.tick()
    assert len(fired) == 0
