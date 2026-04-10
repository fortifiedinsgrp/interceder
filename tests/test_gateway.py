"""Tests for the Gateway FastAPI app and service lifecycle."""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from interceder.gateway.app import build_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(build_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "gateway"


def test_root_serves_placeholder_html() -> None:
    client = TestClient(build_app())
    resp = client.get("/")
    assert resp.status_code == 200
    assert "interceder" in resp.text.lower()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.timeout(25)
def test_gateway_service_starts_and_stops_on_sigterm(
    tmp_interceder_home: Path,
) -> None:
    port = _free_port()
    env = {
        **os.environ,
        "INTERCEDER_HOME": str(tmp_interceder_home),
        "INTERCEDER_GATEWAY_HOST": "127.0.0.1",
        "INTERCEDER_GATEWAY_PORT": str(port),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "interceder", "gateway"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Poll /health until ready (or timeout).
        deadline = time.monotonic() + 10
        ready = False
        while time.monotonic() < deadline:
            try:
                r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                if r.status_code == 200:
                    ready = True
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        if not ready:
            proc.kill()
            out, err = proc.communicate()
            pytest.fail(
                f"gateway never became ready\nstdout: {out.decode()}\n"
                f"stderr: {err.decode()}"
            )

        proc.send_signal(signal.SIGTERM)
        try:
            rc = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("gateway did not exit within 10s of SIGTERM")
        assert rc == 0, f"gateway exited with code {rc}"
    finally:
        if proc.poll() is None:
            proc.kill()
