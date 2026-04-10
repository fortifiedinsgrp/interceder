"""Canonical Message schema — single source of truth for all queue boundaries.

Both Gateway↔Manager queue (inbox/outbox) and the memory archive (Phase 3)
normalize to this shape. Clients (Slack renderer, webapp WS) adapt from it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttachmentRef:
    sha256: str
    mime_type: str
    label: str = ""


@dataclass
class Message:
    id: str
    correlation_id: str
    source: str  # slack | webapp | scheduler:* | manager_proactive | worker_event | approval
    kind: str  # text | tool_result | attachment | approval_request | approval_resolution | worker_update | proactive
    content: str
    created_at: int  # unix timestamp
    user_id: str = "me"
    metadata: dict[str, Any] = field(default_factory=dict)
    attachments: list[AttachmentRef] = field(default_factory=list)
    processed_at: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for SQLite row insertion."""
        return {
            "id": self.id,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "source": self.source,
            "kind": self.kind,
            "content": self.content,
            "metadata_json": json.dumps(self.metadata),
            "created_at": self.created_at,
            "processed_at": self.processed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Message:
        """Reconstruct from a SQLite Row or plain dict."""
        meta_raw = d.get("metadata_json", "{}")
        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
        return cls(
            id=d["id"],
            correlation_id=d["correlation_id"],
            user_id=d.get("user_id", "me"),
            source=d["source"],
            kind=d["kind"],
            content=d["content"],
            metadata=meta,
            created_at=d["created_at"],
            processed_at=d.get("processed_at"),
        )
