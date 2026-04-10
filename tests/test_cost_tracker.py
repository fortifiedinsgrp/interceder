"""Tests for per-tool cost tracking."""
from __future__ import annotations

from pathlib import Path

from interceder import config
from interceder.memory import db, runner
from interceder.tools.cost_tracker import CostTracker


def _setup(tmp_interceder_home: Path) -> CostTracker:
    runner.migrate()
    conn = db.connect(config.db_path())
    return CostTracker(conn)


def test_record_cost(tmp_interceder_home: Path) -> None:
    tracker = _setup(tmp_interceder_home)
    tracker.record(tool="veo", key_name="interceder/veo_api_key", usd_cents=150)
    total = tracker.total_cents(tool="veo")
    assert total == 150


def test_total_by_tool(tmp_interceder_home: Path) -> None:
    tracker = _setup(tmp_interceder_home)
    tracker.record(tool="veo", key_name="k1", usd_cents=100)
    tracker.record(tool="veo", key_name="k1", usd_cents=50)
    tracker.record(tool="nano_banana", key_name="k2", usd_cents=200)
    assert tracker.total_cents(tool="veo") == 150
    assert tracker.total_cents(tool="nano_banana") == 200


def test_monthly_total(tmp_interceder_home: Path) -> None:
    tracker = _setup(tmp_interceder_home)
    tracker.record(tool="veo", key_name="k1", usd_cents=500)
    report = tracker.monthly_report()
    assert "veo" in report
    assert report["veo"] == 500
