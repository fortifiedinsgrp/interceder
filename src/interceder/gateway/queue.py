"""Inbox / outbox SQLite queue helpers.

The inbox and outbox tables were created in 0001_init.sql (Phase 0).
These functions provide the read/write interface the Gateway and
Manager Supervisor use to pass messages across the process boundary.

All operations are idempotent (INSERT OR IGNORE on the primary key).
"""
from __future__ import annotations

import os
import sqlite3
import time

from interceder.schema import Message


def enqueue_inbox(conn: sqlite3.Connection, msg: Message) -> None:
    d = msg.to_dict()
    conn.execute(
        """
        INSERT OR IGNORE INTO inbox
            (id, correlation_id, user_id, source, kind, content, metadata_json, created_at)
        VALUES (:id, :correlation_id, :user_id, :source, :kind, :content, :metadata_json, :created_at)
        """,
        d,
    )


def drain_inbox(
    conn: sqlite3.Connection, *, limit: int = 50
) -> list[sqlite3.Row]:
    """Atomically claim up to `limit` queued inbox rows for this process."""
    pid = os.getpid()
    now = int(time.time())
    conn.execute("BEGIN")
    ids = [
        row["id"]
        for row in conn.execute(
            """
            SELECT id FROM inbox
            WHERE status = 'queued'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    ]
    for msg_id in ids:
        conn.execute(
            "UPDATE inbox SET status='in_flight', in_flight_pid=?, processed_at=? WHERE id=?",
            (pid, now, msg_id),
        )
    conn.execute("COMMIT")
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    return conn.execute(
        f"SELECT * FROM inbox WHERE id IN ({placeholders})",
        ids,
    ).fetchall()


def complete_inbox(conn: sqlite3.Connection, msg_id: str) -> None:
    conn.execute(
        "UPDATE inbox SET status='completed', processed_at=? WHERE id=?",
        (int(time.time()), msg_id),
    )


def fail_inbox(conn: sqlite3.Connection, msg_id: str) -> None:
    conn.execute(
        "UPDATE inbox SET status='failed', processed_at=? WHERE id=?",
        (int(time.time()), msg_id),
    )


def enqueue_outbox(
    conn: sqlite3.Connection,
    msg: Message,
    inbox_id: str | None = None,
) -> None:
    d = msg.to_dict()
    conn.execute(
        """
        INSERT OR IGNORE INTO outbox
            (id, correlation_id, inbox_id, source, kind, content, metadata_json, created_at)
        VALUES (:id, :correlation_id, :inbox_id, :source, :kind, :content, :metadata_json, :created_at)
        """,
        {**d, "inbox_id": inbox_id},
    )


def drain_outbox(
    conn: sqlite3.Connection, *, limit: int = 50
) -> list[sqlite3.Row]:
    conn.execute("BEGIN")
    rows = conn.execute(
        """
        SELECT * FROM outbox
        WHERE status = 'queued'
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE outbox SET status='in_flight' WHERE id=?",
            (row["id"],),
        )
    conn.execute("COMMIT")
    return rows


def mark_delivered(
    conn: sqlite3.Connection, msg_id: str, *, channel: str
) -> None:
    now = int(time.time())
    if channel == "slack":
        conn.execute(
            "UPDATE outbox SET delivered_slack=1, delivered_at=? WHERE id=?",
            (now, msg_id),
        )
    elif channel == "web":
        conn.execute(
            "UPDATE outbox SET delivered_web=1, delivered_at=? WHERE id=?",
            (now, msg_id),
        )
    # Mark fully delivered when both channels done
    conn.execute(
        """
        UPDATE outbox SET status='delivered'
        WHERE id=? AND delivered_slack=1 AND delivered_web=1
        """,
        (msg_id,),
    )
