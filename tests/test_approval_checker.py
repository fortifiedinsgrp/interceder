"""Tests for Approval.check — the decision engine."""
from __future__ import annotations

import time
from pathlib import Path

from interceder import config
from interceder.approval.checker import ApprovalChecker, Decision
from interceder.memory import db, runner


def _setup(tmp_interceder_home: Path) -> ApprovalChecker:
    runner.migrate()
    conn = db.connect(config.db_path())
    return ApprovalChecker(conn)


def test_tier_0_allows(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    decision = checker.check("Read", {"file_path": "/Users/me/code/file.py"}, actor="manager")
    assert decision.outcome == "allow"


def test_tier_1_needs_approval(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    decision = checker.check("Bash", {"command": "git push origin feature"}, actor="manager")
    assert decision.outcome == "needs_approval"
    assert decision.approval_id is not None


def test_tier_2_blocks(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    decision = checker.check("Bash", {"command": "rm -rf ~"}, actor="manager")
    assert decision.outcome == "blocked"


def test_approval_resolve_approve(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    decision = checker.check("Bash", {"command": "git push origin feature"}, actor="manager")
    checker.resolve(decision.approval_id, approved=True, resolved_by="slack")
    row = checker.get_approval(decision.approval_id)
    assert row["status"] == "approved"


def test_approval_resolve_deny(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    decision = checker.check("Bash", {"command": "git push origin feature"}, actor="manager")
    checker.resolve(decision.approval_id, approved=False, resolved_by="webapp")
    row = checker.get_approval(decision.approval_id)
    assert row["status"] == "denied"
