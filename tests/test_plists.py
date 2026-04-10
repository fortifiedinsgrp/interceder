"""Verify the launchd plist templates parse and contain required keys."""
from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY = REPO_ROOT / "deploy"


@pytest.mark.parametrize(
    "plist_name,label",
    [
        ("com.interceder.gateway.plist", "com.interceder.gateway"),
        ("com.interceder.manager.plist", "com.interceder.manager"),
    ],
)
def test_plist_has_required_keys(plist_name: str, label: str) -> None:
    path = DEPLOY / plist_name
    assert path.exists(), f"missing {plist_name}"
    with path.open("rb") as f:
        data = plistlib.load(f)

    assert data["Label"] == label
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] is True
    assert isinstance(data["ProgramArguments"], list)
    assert len(data["ProgramArguments"]) >= 1
    assert "StandardOutPath" in data
    assert "StandardErrorPath" in data
    env = data["EnvironmentVariables"]
    assert "INTERCEDER_HOME" in env


def test_gateway_plist_references_gateway_subcommand() -> None:
    with (DEPLOY / "com.interceder.gateway.plist").open("rb") as f:
        data = plistlib.load(f)
    assert "gateway" in data["ProgramArguments"]


def test_manager_plist_references_manager_subcommand() -> None:
    with (DEPLOY / "com.interceder.manager.plist").open("rb") as f:
        data = plistlib.load(f)
    assert "manager" in data["ProgramArguments"]
