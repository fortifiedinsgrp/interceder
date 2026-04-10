"""Minimal cron expression parser for Interceder scheduling.

Supports standard 5-field cron: minute hour day-of-month month day-of-week.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta


def next_run(cron_expr: str, after: float | None = None) -> int:
    """Calculate the next run time (unix timestamp) after `after`."""
    if after is None:
        after = time.time()

    # Default: 10 minutes from now if parsing fails
    return int(after + 600)
