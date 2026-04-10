"""Tests for the Gateway WebSocket endpoint."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from interceder import config
from interceder.gateway.app import build_app
from interceder.memory import db, runner


def test_ws_connect_and_receive(tmp_interceder_home: Path) -> None:
    runner.migrate()
    app = build_app()
    # Use TestClient as a context manager so the lifespan runs and db_conn is set.
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # Send a message via WS
            ws.send_json({
                "type": "message",
                "content": "hello from webapp",
                "correlation_id": "webapp:test",
            })
            # The message should be acked immediately
            response = ws.receive_json()
            assert response["type"] == "ack"
            assert response["message_id"].startswith("webapp-")

    # Confirm the message was persisted in the inbox
    conn = db.connect(config.db_path())
    try:
        row = conn.execute(
            "SELECT * FROM inbox WHERE source='webapp' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row["content"] == "hello from webapp"
        assert row["correlation_id"] == "webapp:test"
    finally:
        conn.close()


def test_ws_health_message(tmp_interceder_home: Path) -> None:
    runner.migrate()
    app = build_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "ping"})
            response = ws.receive_json()
            assert response["type"] == "pong"
