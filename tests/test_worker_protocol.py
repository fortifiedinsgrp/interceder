"""Tests for the worker JSONL event protocol."""
from __future__ import annotations

import json

from interceder.worker.protocol import (
    WorkerEvent,
    ProgressEvent,
    DoneEvent,
    ErrorEvent,
    serialize_event,
    parse_event,
)


def test_progress_event_roundtrip() -> None:
    evt = ProgressEvent(worker_id="w1", message="running tests", percent=50)
    line = serialize_event(evt)
    parsed = parse_event(line)
    assert isinstance(parsed, ProgressEvent)
    assert parsed.worker_id == "w1"
    assert parsed.percent == 50


def test_done_event_roundtrip() -> None:
    evt = DoneEvent(worker_id="w1", summary="implemented search bar", diff_ref="abc123")
    line = serialize_event(evt)
    parsed = parse_event(line)
    assert isinstance(parsed, DoneEvent)
    assert parsed.summary == "implemented search bar"


def test_error_event_roundtrip() -> None:
    evt = ErrorEvent(worker_id="w1", error="test failed", traceback="...")
    line = serialize_event(evt)
    parsed = parse_event(line)
    assert isinstance(parsed, ErrorEvent)
    assert parsed.error == "test failed"


def test_serialize_is_single_line_json() -> None:
    evt = ProgressEvent(worker_id="w1", message="hi", percent=0)
    line = serialize_event(evt)
    assert "\n" not in line
    data = json.loads(line)
    assert data["type"] == "progress"
