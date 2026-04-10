"""AFK grant management — time-bounded autopilot approvals.

Grants auto-approve Tier 1 actions matching their scope. Tier 2 is NEVER
affected by AFK grants. Grants auto-expire and are fully audit-logged.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from typing import Any

log = logging.getLogger("interceder.approval.afk")


class AFKManager:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_grant(
        self,
        *,
        scope: dict[str, Any],
        duration_seconds: int,
    ) -> str:
        gid = f"afk-{uuid.uuid4().hex[:12]}"
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO afk_grants (id, scope_json, granted_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (gid, json.dumps(scope), now, now + duration_seconds),
        )
        log.info("created AFK grant %s (expires in %ds)", gid, duration_seconds)
        return gid

    def get_grant(self, grant_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT * FROM afk_grants WHERE id=?", (grant_id,)
        ).fetchone()
        return dict(row) if row else {}

    def find_matching_grant(
        self,
        *,
        action: str,
        tier: int,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Find an active AFK grant that covers this action."""
        # Tier 2 is NEVER covered by AFK grants
        if tier >= 2:
            return None

        now = int(time.time())
        rows = self._conn.execute(
            "SELECT * FROM afk_grants WHERE expires_at > ? AND revoked_at IS NULL",
            (now,),
        ).fetchall()

        for row in rows:
            scope = json.loads(row["scope_json"])
            granted_tiers = scope.get("tiers", [])
            if tier not in granted_tiers:
                continue

            granted_repos = scope.get("repos", [])
            ctx_repo = context.get("repo", "")
            if granted_repos and ctx_repo:
                if not any(ctx_repo.startswith(r) for r in granted_repos):
                    continue

            return dict(row)

        return None

    def revoke_grant(self, grant_id: str) -> None:
        now = int(time.time())
        self._conn.execute(
            "UPDATE afk_grants SET revoked_at=? WHERE id=?",
            (now, grant_id),
        )
        log.info("revoked AFK grant %s", grant_id)

    def list_active_grants(self) -> list[dict[str, Any]]:
        now = int(time.time())
        rows = self._conn.execute(
            "SELECT * FROM afk_grants WHERE expires_at > ? AND revoked_at IS NULL",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]
