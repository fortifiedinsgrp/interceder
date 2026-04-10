"""Tests for the Gateway REST API serving dashboard data."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from interceder import config
from interceder.gateway.app import build_app
from interceder.memory import db, runner


def _setup(tmp_interceder_home: Path) -> TestClient:
    runner.migrate()
    return TestClient(build_app())


def test_api_workers_list(tmp_interceder_home: Path) -> None:
    client = _setup(tmp_interceder_home)
    resp = client.get("/api/workers")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_api_approvals_list(tmp_interceder_home: Path) -> None:
    client = _setup(tmp_interceder_home)
    resp = client.get("/api/approvals")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_api_memory_search(tmp_interceder_home: Path) -> None:
    client = _setup(tmp_interceder_home)
    resp = client.get("/api/memory/search?q=test")
    assert resp.status_code == 200
    assert "results" in resp.json()
