"""Tests for the Manager Supervisor and its service lifecycle."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from interceder import config
from interceder.manager.supervisor import Supervisor


def test_supervisor_start_opens_db(tmp_interceder_home: Path) -> None:
    # Migrations must run first so db.connect() has a schema to open.
    from interceder.memory import runner

    runner.migrate()

    sup = Supervisor()
    sup.start()
    try:
        assert sup.is_running
        assert config.db_path().exists()
    finally:
        sup.stop()
    assert not sup.is_running


def test_supervisor_tick_is_safe_when_running(tmp_interceder_home: Path) -> None:
    from interceder.memory import runner

    runner.migrate()
    sup = Supervisor()
    sup.start()
    try:
        for _ in range(5):
            sup.tick()  # no-op heartbeat, must not raise
    finally:
        sup.stop()


def test_supervisor_tick_is_noop_when_stopped(tmp_interceder_home: Path) -> None:
    sup = Supervisor()
    # tick() before start() must not raise and must not open resources
    sup.tick()
    assert not sup.is_running


@pytest.mark.timeout(25)
def test_manager_service_starts_and_stops_on_sigterm(
    tmp_interceder_home: Path,
) -> None:
    env = {**os.environ, "INTERCEDER_HOME": str(tmp_interceder_home)}
    # Bootstrap the DB so the Supervisor has a schema to open.
    subprocess.run(
        [sys.executable, "-m", "interceder", "migrate"], env=env, check=True
    )

    proc = subprocess.Popen(
        [sys.executable, "-m", "interceder", "manager"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Let the Supervisor reach its main loop. 1.5s is plenty for a local
        # Python import + db.connect() + one tick.
        time.sleep(1.5)
        assert proc.poll() is None, (
            f"manager crashed on startup; stderr:\n{proc.stderr.read().decode()}"
        )

        proc.send_signal(signal.SIGTERM)
        try:
            rc = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("manager did not exit within 10s of SIGTERM")
        assert rc == 0, f"manager exited with code {rc}"
    finally:
        if proc.poll() is None:
            proc.kill()
