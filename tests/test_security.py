"""Security tests — verify Tier 2 blocks are enforced."""
from __future__ import annotations

from pathlib import Path

from interceder import config
from interceder.approval.checker import ApprovalChecker
from interceder.memory import db, runner


def _setup(tmp_interceder_home: Path) -> ApprovalChecker:
    runner.migrate()
    conn = db.connect(config.db_path())
    return ApprovalChecker(conn)


def test_rm_rf_root_blocked(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    d = checker.check("Bash", {"command": "rm -rf /"}, actor="worker:w1")
    assert d.outcome == "blocked"
    assert d.tier == 2


def test_rm_rf_home_blocked(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    d = checker.check("Bash", {"command": "rm -rf ~"}, actor="worker:w1")
    assert d.outcome == "blocked"


def test_force_push_main_blocked(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    d = checker.check("Bash", {"command": "git push --force origin main"}, actor="manager")
    assert d.outcome == "blocked"


def test_ssh_write_blocked(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    d = checker.check("Edit", {"file_path": "/Users/me/.ssh/config"}, actor="manager")
    assert d.outcome == "blocked"


def test_keychain_access_blocked(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    d = checker.check("Read", {"file_path": "/Users/me/Library/Keychains/login.keychain"}, actor="manager")
    assert d.outcome == "blocked"


def test_stripe_api_blocked(tmp_interceder_home: Path) -> None:
    checker = _setup(tmp_interceder_home)
    d = checker.check("Bash", {"command": "curl stripe.com/api/charges"}, actor="worker:w1")
    assert d.outcome == "blocked"
