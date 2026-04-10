"""Drain the inbox and feed each message through the Manager session.

Each queued inbox row is:
1. Claimed (status → in_flight)
2. Sent to the ManagerSession as a turn
3. The reply is written to the outbox
4. Inbox row marked completed (or failed on error)
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid

from interceder.gateway.queue import (
    complete_inbox,
    drain_inbox,
    enqueue_outbox,
    fail_inbox,
)
from interceder.manager.session import ManagerSession
from interceder.schema import Message

log = logging.getLogger("interceder.manager.inbox_drain")


def process_inbox(
    conn: sqlite3.Connection,
    session: ManagerSession,
    *,
    limit: int = 10,
) -> int:
    """Process up to `limit` queued inbox messages. Returns count processed."""
    rows = drain_inbox(conn, limit=limit)
    processed = 0

    for row in rows:
        msg_id = row["id"]
        content = row["content"]
        correlation = row["correlation_id"]
        meta = json.loads(row["metadata_json"])

        try:
            reply_text = session.send(content)

            reply_msg = Message(
                id=str(uuid.uuid4()),
                correlation_id=correlation,
                source="manager",
                kind="text",
                content=reply_text,
                metadata={"reply_channel": meta.get("slack_channel", "")},
                created_at=int(time.time()),
            )
            enqueue_outbox(conn, reply_msg, inbox_id=msg_id)
            complete_inbox(conn, msg_id)
            processed += 1
            log.info("processed inbox %s → outbox %s", msg_id, reply_msg.id)

        except Exception:
            log.exception("failed to process inbox %s", msg_id)
            fail_inbox(conn, msg_id)

    return processed
