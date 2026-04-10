"""Tests for the inbox/outbox SQLite queue helpers."""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from interceder import config
from interceder.memory import db, runner
from interceder.gateway.queue import (
    enqueue_inbox,
    drain_inbox,
    complete_inbox,
    fail_inbox,
    enqueue_outbox,
    drain_outbox,
    mark_delivered,
)
from interceder.schema import Message


def _setup_db(tmp_interceder_home: Path) -> None:
    runner.migrate()


def _make_msg(**overrides: object) -> Message:
    defaults = {
        "id": str(uuid.uuid4()),
        "correlation_id": "conv-1",
        "source": "slack",
        "kind": "text",
        "content": "hello",
        "created_at": int(time.time()),
    }
    defaults.update(overrides)
    return Message(**defaults)


def test_enqueue_inbox_roundtrip(tmp_interceder_home: Path) -> None:
    _setup_db(tmp_interceder_home)
    conn = db.connect(config.db_path())
    try:
        msg = _make_msg(id="msg-inbox-1")
        enqueue_inbox(conn, msg)
        rows = drain_inbox(conn, limit=10)
        assert len(rows) == 1
        assert rows[0]["id"] == "msg-inbox-1"
        assert rows[0]["status"] == "in_flight"
    finally:
        conn.close()


def test_drain_inbox_skips_completed(tmp_interceder_home: Path) -> None:
    _setup_db(tmp_interceder_home)
    conn = db.connect(config.db_path())
    try:
        msg = _make_msg(id="msg-done")
        enqueue_inbox(conn, msg)
        rows = drain_inbox(conn, limit=10)
        complete_inbox(conn, "msg-done")
        rows2 = drain_inbox(conn, limit=10)
        assert len(rows2) == 0
    finally:
        conn.close()


def test_enqueue_outbox_roundtrip(tmp_interceder_home: Path) -> None:
    _setup_db(tmp_interceder_home)
    conn = db.connect(config.db_path())
    try:
        msg = _make_msg(id="msg-out-1", source="manager")
        enqueue_outbox(conn, msg, inbox_id="msg-inbox-1")
        rows = drain_outbox(conn, limit=10)
        assert len(rows) == 1
        assert rows[0]["id"] == "msg-out-1"
        assert rows[0]["inbox_id"] == "msg-inbox-1"
    finally:
        conn.close()


def test_mark_delivered_slack(tmp_interceder_home: Path) -> None:
    _setup_db(tmp_interceder_home)
    conn = db.connect(config.db_path())
    try:
        msg = _make_msg(id="msg-deliver")
        enqueue_outbox(conn, msg)
        drain_outbox(conn, limit=10)
        mark_delivered(conn, "msg-deliver", channel="slack")
        row = conn.execute(
            "SELECT delivered_slack, delivered_web FROM outbox WHERE id=?",
            ("msg-deliver",),
        ).fetchone()
        assert row["delivered_slack"] == 1
        assert row["delivered_web"] == 0
    finally:
        conn.close()


def test_inbox_idempotent_insert(tmp_interceder_home: Path) -> None:
    _setup_db(tmp_interceder_home)
    conn = db.connect(config.db_path())
    try:
        msg = _make_msg(id="msg-dup")
        enqueue_inbox(conn, msg)
        enqueue_inbox(conn, msg)  # duplicate — should be ignored
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM inbox WHERE id=?", ("msg-dup",)
        ).fetchone()["c"]
        assert count == 1
    finally:
        conn.close()
