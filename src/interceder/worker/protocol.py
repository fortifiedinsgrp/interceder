"""Worker JSONL event protocol.

Workers write one JSON object per line to stdout. The Supervisor reads
these lines and routes events appropriately.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class WorkerEvent:
    worker_id: str
    type: str = ""


@dataclass
class ProgressEvent(WorkerEvent):
    type: str = "progress"
    message: str = ""
    percent: int = 0


@dataclass
class ToolCallEvent(WorkerEvent):
    type: str = "tool_call"
    tool_name: str = ""
    args_json: str = "{}"


@dataclass
class DoneEvent(WorkerEvent):
    type: str = "done"
    summary: str = ""
    diff_ref: str = ""


@dataclass
class ErrorEvent(WorkerEvent):
    type: str = "error"
    error: str = ""
    traceback: str = ""


@dataclass
class NeedsApprovalEvent(WorkerEvent):
    type: str = "needs_approval"
    action: str = ""
    context_json: str = "{}"


_EVENT_TYPES: dict[str, type[WorkerEvent]] = {
    "progress": ProgressEvent,
    "tool_call": ToolCallEvent,
    "done": DoneEvent,
    "error": ErrorEvent,
    "needs_approval": NeedsApprovalEvent,
}


def serialize_event(event: WorkerEvent) -> str:
    """Serialize to a single-line JSON string."""
    return json.dumps(asdict(event), separators=(",", ":"))


def parse_event(line: str) -> WorkerEvent:
    """Parse a single JSONL line into the appropriate event type."""
    data = json.loads(line.strip())
    event_type = data.get("type", "")
    cls = _EVENT_TYPES.get(event_type, WorkerEvent)
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
