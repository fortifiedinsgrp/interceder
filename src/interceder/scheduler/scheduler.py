"""Scheduler — register, tick, and manage cron-like recurring tasks."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from typing import Any

from interceder.scheduler.cron import next_run

log = logging.getLogger("interceder.scheduler")


class Scheduler:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def register(
        self,
        *,
        name: str,
        cron_expr: str,
        prompt: str,
        scope: dict[str, Any] | None = None,
        next_run_at: int | None = None,
    ) -> str:
        sid = f"sched-{uuid.uuid4().hex[:12]}"
        now = int(time.time())
        if next_run_at is None:
            next_run_at = next_run(cron_expr, after=now)
        self._conn.execute(
            """
            INSERT INTO schedules (id, name, cron_expr, prompt, scope_json, next_run_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (sid, name, cron_expr, prompt, json.dumps(scope or {}), next_run_at, now),
        )
        log.info("registered schedule %s: %s", sid, name)
        return sid

    def list_schedules(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM schedules ORDER BY next_run_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def tick(self) -> list[dict[str, Any]]:
        """Check for due schedules. Returns list of fired schedule dicts."""
        now = int(time.time())
        rows = self._conn.execute(
            "SELECT * FROM schedules WHERE enabled=1 AND next_run_at <= ?",
            (now,),
        ).fetchall()

        fired = []
        for row in rows:
            sid = row["id"]
            cron_expr = row["cron_expr"]
            self._conn.execute(
                "UPDATE schedules SET last_run_at=?, next_run_at=? WHERE id=?",
                (now, next_run(cron_expr, after=now), sid),
            )
            fired.append(dict(row))
            log.info("fired schedule: %s", row["name"])

        return fired

    def set_enabled(self, schedule_id: str, enabled: bool) -> None:
        self._conn.execute(
            "UPDATE schedules SET enabled=? WHERE id=?",
            (1 if enabled else 0, schedule_id),
        )
