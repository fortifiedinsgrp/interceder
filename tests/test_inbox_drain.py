"""Tests for the inbox drain loop — feeds messages to the Manager session."""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from interceder import config
from interceder.gateway.queue import enqueue_inbox
from interceder.manager.inbox_drain import process_inbox
from interceder.manager.session import ManagerSession
from interceder.memory import db, runner
from interceder.schema import Message
from tests.stubs.agent_sdk_stub import StubAgentSession


def _setup(tmp_interceder_home: Path) -> None:
    runner.migrate()


def _make_inbox_msg(**overrides: object) -> Message:
    defaults = {
        "id": str(uuid.uuid4()),
        "correlation_id": "slack:D01234",
        "source": "slack",
        "kind": "text",
        "content": "hello from user",
        "metadata": {"slack_channel": "D01234"},
        "created_at": int(time.time()),
    }
    defaults.update(overrides)
    return Message(**defaults)


def test_process_inbox_sends_to_session(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())
    stub = StubAgentSession()
    session = ManagerSession(agent_session=stub)
    try:
        msg = _make_inbox_msg(content="what's up?")
        enqueue_inbox(conn, msg)
        count = process_inbox(conn, session)
        assert count == 1
        assert len(stub.turns) == 1
        assert stub.turns[0].user_message == "what's up?"
    finally:
        conn.close()


def test_process_inbox_writes_reply_to_outbox(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())
    stub = StubAgentSession()
    session = ManagerSession(agent_session=stub)
    try:
        msg = _make_inbox_msg(content="tell me something")
        enqueue_inbox(conn, msg)
        process_inbox(conn, session)
        row = conn.execute(
            "SELECT * FROM outbox ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert "Echo: tell me something" in row["content"]
        assert row["source"] == "manager"
    finally:
        conn.close()


def test_process_inbox_marks_completed(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())
    stub = StubAgentSession()
    session = ManagerSession(agent_session=stub)
    try:
        msg = _make_inbox_msg(id="msg-complete-check")
        enqueue_inbox(conn, msg)
        process_inbox(conn, session)
        row = conn.execute(
            "SELECT status FROM inbox WHERE id=?", ("msg-complete-check",)
        ).fetchone()
        assert row["status"] == "completed"
    finally:
        conn.close()


def test_process_inbox_noop_when_empty(tmp_interceder_home: Path) -> None:
    _setup(tmp_interceder_home)
    conn = db.connect(config.db_path())
    stub = StubAgentSession()
    session = ManagerSession(agent_session=stub)
    try:
        count = process_inbox(conn, session)
        assert count == 0
    finally:
        conn.close()
