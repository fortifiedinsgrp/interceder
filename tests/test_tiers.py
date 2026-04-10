"""Tests for tier classification of actions."""
from __future__ import annotations

from interceder.approval.tiers import classify


def test_read_is_tier_0() -> None:
    assert classify("Read", {"file_path": "/Users/me/code/repo/file.py"}) == 0


def test_git_commit_is_tier_0() -> None:
    assert classify("Bash", {"command": "git commit -m 'fix'"}) == 0


def test_git_push_is_tier_1() -> None:
    assert classify("Bash", {"command": "git push origin feature-branch"}) == 1


def test_git_force_push_main_is_tier_2() -> None:
    assert classify("Bash", {"command": "git push --force origin main"}) == 2


def test_rm_rf_home_is_tier_2() -> None:
    assert classify("Bash", {"command": "rm -rf ~"}) == 2


def test_ssh_write_is_tier_2() -> None:
    assert classify("Edit", {"file_path": "/Users/me/.ssh/config"}) == 2


def test_memory_recall_is_tier_0() -> None:
    assert classify("memory_recall", {"query": "search something"}) == 0


def test_spawn_worker_is_tier_0() -> None:
    assert classify("spawn_worker_process", {}) == 0
