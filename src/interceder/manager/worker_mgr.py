"""Worker manager — register, monitor, and control Worker subprocesses.

Phase 4: manages worker records in SQLite. Actual subprocess spawning
(fork+exec of `python -m interceder.worker`) is wired in Phase 4 Task 4.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from typing import Any

from interceder.worker.sandbox import create_sandbox

log = logging.getLogger("interceder.manager.worker_mgr")


class WorkerManager:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def register(
        self,
        *,
        task_spec: dict[str, Any],
        model: str,
    ) -> str:
        """Register a new Worker. Returns the worker ID."""
        wid = f"w-{uuid.uuid4().hex[:12]}"
        sandbox = create_sandbox(worker_id=wid)
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO workers (id, task_spec_json, status, model, sandbox_dir, started_at)
            VALUES (?, ?, 'queued', ?, ?, ?)
            """,
            (wid, json.dumps(task_spec), model, str(sandbox), now),
        )
        log.info("registered worker %s (model=%s)", wid, model)
        return wid

    def get_worker(self, worker_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT * FROM workers WHERE id=?", (worker_id,)
        ).fetchone()
        return dict(row) if row else {}

    def list_workers(
        self, *, status: str | None = None
    ) -> list[dict[str, Any]]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM workers WHERE status=? ORDER BY started_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM workers ORDER BY started_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_status(
        self,
        worker_id: str,
        status: str,
        *,
        pid: int | None = None,
        summary: str | None = None,
    ) -> None:
        now = int(time.time())
        updates = ["status=?"]
        params: list[Any] = [status]
        if pid is not None:
            updates.append("pid=?")
            params.append(pid)
        if summary is not None:
            updates.append("summary=?")
            params.append(summary)
        if status in ("done", "failed", "killed"):
            updates.append("ended_at=?")
            params.append(now)
        params.append(worker_id)
        self._conn.execute(
            f"UPDATE workers SET {', '.join(updates)} WHERE id=?",
            params,
        )

    def record_event(
        self,
        worker_id: str,
        event_kind: str,
        payload: dict[str, Any],
    ) -> None:
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO worker_events (worker_id, event_kind, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (worker_id, event_kind, json.dumps(payload), now),
        )

    def get_events(
        self, worker_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM worker_events
            WHERE worker_id=?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (worker_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def spawn(
        self,
        *,
        task_spec: dict[str, Any],
        model: str,
    ) -> tuple[str, "subprocess.Popen[bytes]"]:
        """Register + fork a Worker subprocess. Returns (worker_id, process)."""
        import subprocess
        import sys

        wid = self.register(task_spec=task_spec, model=model)
        worker_info = self.get_worker(wid)

        proc = subprocess.Popen(
            [
                sys.executable, "-m", "interceder.worker.runner",
                "--task-spec", json.dumps(task_spec),
                "--worker-id", wid,
                "--model", model,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=worker_info["sandbox_dir"],
        )
        self.update_status(wid, "running", pid=proc.pid)
        log.info("spawned worker %s (pid=%d)", wid, proc.pid)
        return wid, proc
