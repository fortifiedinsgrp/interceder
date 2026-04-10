"""Tests for the Worker manager — spawn, monitor, kill."""
from __future__ import annotations

import time
from pathlib import Path

from interceder import config
from interceder.manager.worker_mgr import WorkerManager
from interceder.memory import db, runner


def _setup(tmp_interceder_home: Path) -> WorkerManager:
    runner.migrate()
    conn = db.connect(config.db_path())
    return WorkerManager(conn)


def test_register_worker(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    wid = mgr.register(
        task_spec={"goal": "implement search bar"},
        model="claude-sonnet-4-6",
    )
    assert wid is not None
    info = mgr.get_worker(wid)
    assert info["status"] == "queued"
    assert info["model"] == "claude-sonnet-4-6"


def test_list_workers(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    mgr.register(task_spec={"goal": "task1"}, model="claude-sonnet-4-6")
    mgr.register(task_spec={"goal": "task2"}, model="claude-haiku-4-5-20251001")
    workers = mgr.list_workers()
    assert len(workers) == 2


def test_mark_worker_done(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    wid = mgr.register(task_spec={"goal": "task"}, model="claude-sonnet-4-6")
    mgr.update_status(wid, "running", pid=12345)
    mgr.update_status(wid, "done", summary="completed search bar")
    info = mgr.get_worker(wid)
    assert info["status"] == "done"
    assert info["summary"] == "completed search bar"


def test_record_event(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    wid = mgr.register(task_spec={"goal": "task"}, model="claude-sonnet-4-6")
    mgr.record_event(wid, "progress", {"message": "50% done"})
    events = mgr.get_events(wid)
    assert len(events) == 1
    assert events[0]["event_kind"] == "progress"
