"""Proactive message engine — rate-limited, quiet-hours-aware.

Eight message classes:
1. worker_done — background task completion
2. approval — Tier 1 action gates
3. failure — crashes, stuck loops, broken tests
4. idle_reflection — what I learned during idle
5. scheduled — scheduled task output
6. opportunistic — pattern-noticing suggestions
7. reminder — memory-triggered reminders
8. briefing — morning/evening digests
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

log = logging.getLogger("interceder.manager.proactive")

# Urgent classes bypass quiet hours
_URGENT_CLASSES = frozenset({"failure", "approval"})


class ProactiveEngine:
    def __init__(
        self,
        *,
        rate_limits: dict[str, int] | None = None,
        quiet_start_hour: int = 23,
        quiet_end_hour: int = 7,
    ) -> None:
        self._rate_limits = rate_limits or {
            "worker_done": 30,
            "approval": 0,
            "failure": 0,
            "idle_reflection": 900,
            "scheduled": 60,
            "opportunistic": 3600,
            "reminder": 300,
            "briefing": 43200,
        }
        self._last_sent: dict[str, float] = {}
        self._quiet_start = quiet_start_hour
        self._quiet_end = quiet_end_hour
        self._digest_queue: list[dict[str, Any]] = []

    def is_quiet_hours(self) -> bool:
        hour = datetime.now().hour
        if self._quiet_start <= self._quiet_end:
            return self._quiet_start <= hour < self._quiet_end
        return hour >= self._quiet_start or hour < self._quiet_end

    def should_send(
        self,
        msg_class: str,
        *,
        urgent: bool = False,
    ) -> bool:
        if urgent or msg_class in _URGENT_CLASSES:
            pass  # bypass quiet hours
        elif self.is_quiet_hours():
            return False

        limit = self._rate_limits.get(msg_class, 0)
        if limit <= 0:
            return True

        last = self._last_sent.get(msg_class, 0)
        return (time.time() - last) >= limit

    def record_sent(self, msg_class: str) -> None:
        self._last_sent[msg_class] = time.time()

    def queue_for_digest(self, msg: dict[str, Any]) -> None:
        self._digest_queue.append(msg)

    def flush_digest(self) -> list[dict[str, Any]]:
        msgs = self._digest_queue.copy()
        self._digest_queue.clear()
        return msgs
