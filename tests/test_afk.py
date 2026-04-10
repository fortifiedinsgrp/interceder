"""Tests for AFK grant management."""
from __future__ import annotations

import time
from pathlib import Path

from interceder import config
from interceder.approval.afk import AFKManager
from interceder.memory import db, runner


def _setup(tmp_interceder_home: Path) -> AFKManager:
    runner.migrate()
    conn = db.connect(config.db_path())
    return AFKManager(conn)


def test_create_grant(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    gid = mgr.create_grant(
        scope={"repos": ["~/code/dashboard"], "tiers": [1]},
        duration_seconds=3600,
    )
    assert gid is not None
    grant = mgr.get_grant(gid)
    assert grant["id"] == gid


def test_grant_matches_scope(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    mgr.create_grant(
        scope={"repos": ["~/code/dashboard"], "tiers": [1]},
        duration_seconds=3600,
    )
    matched = mgr.find_matching_grant(
        action="git push",
        tier=1,
        context={"repo": "~/code/dashboard"},
    )
    assert matched is not None


def test_grant_does_not_match_tier_2(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    mgr.create_grant(
        scope={"repos": ["~/code/dashboard"], "tiers": [1]},
        duration_seconds=3600,
    )
    matched = mgr.find_matching_grant(
        action="rm -rf",
        tier=2,
        context={"repo": "~/code/dashboard"},
    )
    assert matched is None


def test_expired_grant_not_matched(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    mgr.create_grant(
        scope={"repos": ["~/code/dashboard"], "tiers": [1]},
        duration_seconds=0,  # immediately expired
    )
    import time
    time.sleep(0.1)
    matched = mgr.find_matching_grant(
        action="git push",
        tier=1,
        context={"repo": "~/code/dashboard"},
    )
    assert matched is None


def test_revoke_grant(tmp_interceder_home: Path) -> None:
    mgr = _setup(tmp_interceder_home)
    gid = mgr.create_grant(
        scope={"repos": ["~/code/dashboard"], "tiers": [1]},
        duration_seconds=3600,
    )
    mgr.revoke_grant(gid)
    matched = mgr.find_matching_grant(
        action="git push", tier=1, context={"repo": "~/code/dashboard"},
    )
    assert matched is None
