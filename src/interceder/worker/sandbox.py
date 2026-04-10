"""Worker sandbox directory management.

Each Worker gets an isolated subdirectory under INTERCEDER_HOME/workers/.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from interceder import config


def create_sandbox(*, worker_id: str) -> Path:
    """Create and return a fresh sandbox directory for a Worker."""
    sandbox = config.workers_dir() / worker_id
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


def cleanup_sandbox(sandbox: Path) -> None:
    """Remove a sandbox directory and all its contents."""
    if sandbox.exists():
        shutil.rmtree(sandbox)
