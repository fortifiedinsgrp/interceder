"""Memory archive — recall, write, tombstone, entities, hot memory.

This is the Python interface to the memory.sqlite archive. The Manager
calls these methods directly (from the Supervisor) and indirectly (via
custom memory_recall/memory_write tools registered on the Agent SDK session).
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any


class Memory:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    def write_message(
        self,
        *,
        id: str,
        correlation_id: str,
        role: str,
        source: str,
        kind: str,
        content: str,
        created_at: int,
        user_id: str = "me",
        metadata_json: str = "{}",
    ) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO messages
                (id, correlation_id, user_id, source, kind, role, content, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id, correlation_id, user_id, source, kind, role, content, metadata_json, created_at),
        )

    def recall(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """FTS5 search over message content, excluding tombstoned entries."""
        rows = self._conn.execute(
            """
            SELECT m.id, m.correlation_id, m.role, m.source, m.kind,
                   m.content, m.created_at
            FROM messages m
            JOIN messages_fts f ON m.rowid = f.rowid
            WHERE messages_fts MATCH ?
              AND m.tombstoned_at IS NULL
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def tombstone(self, msg_id: str) -> int:
        """Tombstone a message by ID. Returns count of rows affected."""
        now = int(time.time())
        cursor = self._conn.execute(
            "UPDATE messages SET tombstoned_at=? WHERE id=? AND tombstoned_at IS NULL",
            (now, msg_id),
        )
        return cursor.rowcount

    # ------------------------------------------------------------------
    # Entities and facts
    # ------------------------------------------------------------------
    def add_entity(
        self,
        *,
        name: str,
        kind: str,
        properties_json: str = "{}",
        first_seen_msg: str | None = None,
    ) -> int:
        now = int(time.time())
        cursor = self._conn.execute(
            """
            INSERT INTO entities (name, kind, properties_json, first_seen_msg, last_seen_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name, kind) DO UPDATE SET last_seen_at=excluded.last_seen_at
            """,
            (name, kind, properties_json, first_seen_msg, now),
        )
        if cursor.lastrowid:
            return cursor.lastrowid
        row = self._conn.execute(
            "SELECT id FROM entities WHERE name=? AND kind=?", (name, kind)
        ).fetchone()
        return row["id"]

    def add_fact(
        self,
        *,
        entity_id: int,
        claim: str,
        confidence: float = 1.0,
        source_msg_id: str | None = None,
    ) -> int:
        now = int(time.time())
        cursor = self._conn.execute(
            """
            INSERT INTO facts (entity_id, claim, confidence, source_msg_id, extracted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entity_id, claim, confidence, source_msg_id, now),
        )
        return cursor.lastrowid  # type: ignore[return-value]

    def search_entities(
        self,
        name: str,
        *,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        if kind:
            rows = self._conn.execute(
                "SELECT * FROM entities WHERE name LIKE ? AND kind=?",
                (f"%{name}%", kind),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM entities WHERE name LIKE ?",
                (f"%{name}%",),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Hot memory
    # ------------------------------------------------------------------
    def promote(
        self,
        *,
        slot: str,
        content: str,
        priority: int,
        token_estimate: int,
    ) -> int:
        now = int(time.time())
        cursor = self._conn.execute(
            """
            INSERT INTO hot_memory (slot, content, priority, token_estimate, last_touched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (slot, content, priority, token_estimate, now),
        )
        return cursor.lastrowid  # type: ignore[return-value]

    def demote(self, hot_id: int) -> None:
        self._conn.execute("DELETE FROM hot_memory WHERE id=?", (hot_id,))

    def get_hot_memory(self, *, token_budget: int = 4000) -> list[dict[str, Any]]:
        """Return hot memory items within token budget, sorted by priority."""
        rows = self._conn.execute(
            "SELECT * FROM hot_memory ORDER BY priority DESC"
        ).fetchall()
        result = []
        total = 0
        for row in rows:
            if total + row["token_estimate"] > token_budget:
                break
            result.append(dict(row))
            total += row["token_estimate"]
        return result
