"""Tests for worker sandbox directory management."""
from __future__ import annotations

import os
from pathlib import Path

from interceder import config
from interceder.worker.sandbox import create_sandbox, cleanup_sandbox


def test_create_sandbox(tmp_interceder_home: Path) -> None:
    sandbox = create_sandbox(worker_id="w1-test")
    assert sandbox.is_dir()
    assert "w1-test" in sandbox.name
    assert sandbox.parent == config.workers_dir()


def test_create_sandbox_is_unique(tmp_interceder_home: Path) -> None:
    s1 = create_sandbox(worker_id="w1")
    s2 = create_sandbox(worker_id="w2")
    assert s1 != s2


def test_cleanup_sandbox(tmp_interceder_home: Path) -> None:
    sandbox = create_sandbox(worker_id="w-cleanup")
    (sandbox / "scratch.txt").write_text("temp")
    cleanup_sandbox(sandbox)
    assert not sandbox.exists()


def test_cleanup_nonexistent_is_noop(tmp_interceder_home: Path) -> None:
    fake = config.workers_dir() / "nonexistent"
    cleanup_sandbox(fake)  # should not raise
