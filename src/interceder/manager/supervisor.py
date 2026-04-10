"""Manager Supervisor — Phase 0 skeleton.

Phase 2 will grow this into a wrapper around a long-lived Claude Agent SDK
session, with the hot memory curator, tool registrations, inbox-drain loop,
worker supervision, and rate-limit backoff. For Phase 0, it just proves
the supervision loop can boot, open the DB, tick harmlessly, and shut
down cleanly.
"""
from __future__ import annotations

import logging
import sqlite3

from interceder import config
from interceder.memory import db

log = logging.getLogger("interceder.manager.supervisor")


class Supervisor:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        log.info("supervisor starting; db=%s", config.db_path())
        self._conn = db.connect(config.db_path())
        self._running = True
        log.info("supervisor started")

    def tick(self) -> None:
        """One pass of the main loop. Phase 0: no-op heartbeat."""
        if not self._running:
            return
        log.debug("supervisor tick")

    def stop(self) -> None:
        if not self._running and self._conn is None:
            return
        log.info("supervisor stopping")
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._running = False
        log.info("supervisor stopped")
