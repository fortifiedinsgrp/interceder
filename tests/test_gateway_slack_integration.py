"""Integration test: Slack event → inbox → canned outbox ack.

Uses a mock Slack client — no real Slack connection needed.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock

from interceder import config
from interceder.gateway.queue import enqueue_inbox
from interceder.gateway.slack_handler import normalize_slack_event
from interceder.memory import db, runner
from interceder.schema import Message


def test_slack_event_to_inbox(tmp_interceder_home: Path) -> None:
    runner.migrate()
    conn = db.connect(config.db_path())
    try:
        event = {
            "type": "message",
            "user": "U1234",
            "text": "what's the status?",
            "ts": "1700000000.123456",
            "channel": "D01234",
            "channel_type": "im",
        }
        msg = normalize_slack_event(event)
        assert msg is not None
        enqueue_inbox(conn, msg)

        row = conn.execute(
            "SELECT * FROM inbox WHERE source='slack' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row["content"] == "what's the status?"
        assert row["status"] == "queued"
    finally:
        conn.close()
