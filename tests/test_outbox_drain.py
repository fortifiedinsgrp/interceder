"""Tests for the outbox drain loop — sends queued replies to Slack."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock

from interceder import config
from interceder.gateway.outbox_drain import drain_and_send
from interceder.gateway.queue import enqueue_outbox
from interceder.memory import db, runner
from interceder.schema import Message


def _setup(tmp_interceder_home: Path) -> None:
    runner.migrate()


def test_drain_sends_to_slack(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())
    mock_slack = MagicMock()
    try:
        msg = Message(
            id=str(uuid.uuid4()),
            correlation_id="slack:D01234",
            source="manager",
            kind="text",
            content="reply from manager",
            metadata={"reply_channel": "D01234"},
            created_at=int(time.time()),
        )
        enqueue_outbox(conn, msg)
        count = drain_and_send(conn, slack_client=mock_slack)
        assert count == 1
        mock_slack.chat_postMessage.assert_called_once()
        call_kwargs = mock_slack.chat_postMessage.call_args.kwargs
        assert call_kwargs["channel"] == "D01234"
        assert "reply from manager" in call_kwargs["text"]
    finally:
        conn.close()


def test_drain_noop_when_empty(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())
    mock_slack = MagicMock()
    try:
        count = drain_and_send(conn, slack_client=mock_slack)
        assert count == 0
        mock_slack.chat_postMessage.assert_not_called()
    finally:
        conn.close()
