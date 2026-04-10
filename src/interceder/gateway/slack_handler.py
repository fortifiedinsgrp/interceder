"""Normalize Slack Socket Mode events into canonical Message objects.

Only DM (im) messages from the configured user are accepted. Bot messages,
edits, and non-DM channels are ignored.
"""
from __future__ import annotations

import uuid
from typing import Any

from interceder.schema import Message


# Subtypes we always ignore
_IGNORED_SUBTYPES = frozenset({
    "bot_message",
    "message_changed",
    "message_deleted",
    "channel_join",
    "channel_leave",
})


def normalize_slack_event(event: dict[str, Any]) -> Message | None:
    """Convert a Slack message event to a canonical Message, or None to skip."""
    if event.get("type") != "message":
        return None
    if event.get("subtype") in _IGNORED_SUBTYPES:
        return None
    if "user" not in event:
        return None

    user = event["user"]
    text = event.get("text", "")
    ts = event["ts"]
    channel = event.get("channel", "")
    ts_int = int(float(ts))

    metadata: dict[str, Any] = {
        "slack_ts": ts,
        "slack_channel": channel,
    }

    if "files" in event:
        metadata["slack_files"] = [
            {
                "id": f["id"],
                "name": f.get("name", ""),
                "mimetype": f.get("mimetype", ""),
                "url_private_download": f.get("url_private_download", ""),
            }
            for f in event["files"]
        ]

    return Message(
        id=f"slack-{ts}-{uuid.uuid4().hex[:8]}",
        correlation_id=f"slack:{channel}",
        user_id=user,
        source="slack",
        kind="text",
        content=text,
        metadata=metadata,
        created_at=ts_int,
    )
