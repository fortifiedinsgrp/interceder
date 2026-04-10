"""Tests for the canonical Message schema."""
from __future__ import annotations

import json
import time
import uuid

from interceder.schema import Message


def test_message_construction_with_defaults() -> None:
    msg = Message(
        id=str(uuid.uuid4()),
        correlation_id="conv-1",
        source="slack",
        kind="text",
        content="hello world",
        created_at=int(time.time()),
    )
    assert msg.user_id == "me"
    assert msg.metadata == {}
    assert msg.attachments == []
    assert msg.processed_at is None


def test_message_to_dict_roundtrip() -> None:
    msg = Message(
        id="msg-1",
        correlation_id="conv-1",
        source="slack",
        kind="text",
        content="hi",
        created_at=1700000000,
    )
    d = msg.to_dict()
    assert d["id"] == "msg-1"
    assert d["metadata_json"] == "{}"
    restored = Message.from_dict(d)
    assert restored.id == msg.id
    assert restored.content == msg.content


def test_message_metadata_json_roundtrip() -> None:
    meta = {"slack_ts": "1234567890.123456", "channel": "D01234"}
    msg = Message(
        id="msg-2",
        correlation_id="conv-1",
        source="slack",
        kind="text",
        content="hi",
        metadata=meta,
        created_at=1700000000,
    )
    d = msg.to_dict()
    assert json.loads(d["metadata_json"]) == meta
    restored = Message.from_dict(d)
    assert restored.metadata == meta
