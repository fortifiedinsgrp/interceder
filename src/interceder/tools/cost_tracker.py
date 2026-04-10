"""Per-tool cost tracking for third-party APIs."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Any

log = logging.getLogger("interceder.tools.cost_tracker")


class CostTracker:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(
        self,
        *,
        tool: str,
        key_name: str,
        usd_cents: int,
        workflow_id: str | None = None,
        units: dict[str, Any] | None = None,
    ) -> None:
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO costs (tool, key_name, workflow_id, usd_cents, units_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tool, key_name, workflow_id, usd_cents, json.dumps(units or {}), now),
        )

    def total_cents(self, *, tool: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(usd_cents), 0) AS total FROM costs WHERE tool=?",
            (tool,),
        ).fetchone()
        return row["total"]

    def monthly_report(self) -> dict[str, int]:
        """Return total spend per tool for the current calendar month."""
        from datetime import datetime

        now = datetime.now()
        month_start = int(datetime(now.year, now.month, 1).timestamp())
        rows = self._conn.execute(
            """
            SELECT tool, COALESCE(SUM(usd_cents), 0) AS total
            FROM costs WHERE created_at >= ?
            GROUP BY tool
            """,
            (month_start,),
        ).fetchall()
        return {r["tool"]: r["total"] for r in rows}
