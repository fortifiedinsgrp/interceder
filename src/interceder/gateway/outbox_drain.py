"""Drain outbox rows and deliver them to Slack (and eventually webapp).

Phase 1: Slack only. Phase 6 adds webapp WebSocket delivery.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from interceder.gateway.queue import drain_outbox, mark_delivered

log = logging.getLogger("interceder.gateway.outbox_drain")


def drain_and_send(
    conn: sqlite3.Connection,
    *,
    slack_client: Any | None = None,
) -> int:
    """Drain pending outbox rows and send to Slack. Returns count sent."""
    rows = drain_outbox(conn, limit=50)
    sent = 0
    for row in rows:
        msg_id = row["id"]
        content = row["content"]
        meta = json.loads(row["metadata_json"])
        correlation = row["correlation_id"]

        # Determine Slack channel from metadata or correlation_id
        channel = meta.get("reply_channel")
        if not channel and correlation.startswith("slack:"):
            channel = correlation.split(":", 1)[1]

        if slack_client and channel:
            try:
                slack_client.chat_postMessage(
                    channel=channel,
                    text=content,
                )
                mark_delivered(conn, msg_id, channel="slack")
                sent += 1
            except Exception:
                log.exception("failed to send outbox %s to Slack", msg_id)
        else:
            log.warning("outbox %s: no Slack channel, skipping", msg_id)

    return sent
