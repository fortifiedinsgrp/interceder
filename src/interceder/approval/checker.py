"""Approval checker — Tier 0/1/2 decision engine with audit logging."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from interceder.approval.tiers import classify

log = logging.getLogger("interceder.approval.checker")

_DEFAULT_EXPIRY_SECONDS = 4 * 60 * 60  # 4 hours


@dataclass
class Decision:
    outcome: str  # allow | needs_approval | blocked
    tier: int
    approval_id: str | None = None
    reason: str = ""


class ApprovalChecker:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def check(
        self,
        tool_name: str,
        context: dict[str, Any],
        *,
        actor: str = "manager",
    ) -> Decision:
        tier = classify(tool_name, context)
        now = int(time.time())

        if tier == 0:
            self._audit(actor, tool_name, tier, "allow", context, now)
            return Decision(outcome="allow", tier=0)

        if tier == 2:
            self._audit(actor, tool_name, tier, "blocked", context, now)
            return Decision(
                outcome="blocked", tier=2,
                reason=f"Tier 2: action '{tool_name}' is hard-blocked",
            )

        # Tier 1: queue for approval
        approval_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO approvals (id, action, context_json, tier, status, requested_by, expires_at, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (approval_id, tool_name, json.dumps(context), tier, actor,
             now + _DEFAULT_EXPIRY_SECONDS, now),
        )
        self._audit(actor, tool_name, tier, "needs_approval", context, now)
        return Decision(
            outcome="needs_approval", tier=1,
            approval_id=approval_id,
            reason=f"Tier 1: '{tool_name}' requires approval",
        )

    def resolve(
        self,
        approval_id: str | None,
        *,
        approved: bool,
        resolved_by: str,
    ) -> None:
        if approval_id is None:
            return
        status = "approved" if approved else "denied"
        now = int(time.time())
        self._conn.execute(
            "UPDATE approvals SET status=?, resolved_by=?, resolved_at=? WHERE id=?",
            (status, resolved_by, now, approval_id),
        )

    def get_approval(self, approval_id: str | None) -> dict[str, Any]:
        if approval_id is None:
            return {}
        row = self._conn.execute(
            "SELECT * FROM approvals WHERE id=?", (approval_id,)
        ).fetchone()
        return dict(row) if row else {}

    def _audit(
        self,
        actor: str,
        action: str,
        tier: int,
        outcome: str,
        context: dict[str, Any],
        created_at: int,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_log (actor, action, tier, outcome, context_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor, action, tier, outcome, json.dumps(context), created_at),
        )
