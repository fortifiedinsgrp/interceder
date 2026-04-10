"""REST API endpoints for the webapp dashboard.

All endpoints read from memory.sqlite (read-only from the Gateway's perspective).
Write operations (approve/deny, settings changes) go through the inbox queue
to the Manager.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Query

from interceder import config
from interceder.memory import db

log = logging.getLogger("interceder.gateway.api")

router = APIRouter(prefix="/api")


def _get_conn():
    return db.connect(config.db_path())


@router.get("/workers")
def list_workers(status: str | None = None) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM workers WHERE status=? ORDER BY started_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM workers ORDER BY started_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        log.exception("list_workers failed")
        return []
    finally:
        conn.close()


@router.get("/approvals")
def list_approvals(status: str = "pending") -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM approvals WHERE status=? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        log.exception("list_approvals failed")
        return []
    finally:
        conn.close()


@router.get("/memory/search")
def search_memory(q: str = Query(..., min_length=1)) -> dict[str, Any]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT m.id, m.role, m.source, m.kind, m.content, m.created_at
            FROM messages m
            JOIN messages_fts f ON m.rowid = f.rowid
            WHERE messages_fts MATCH ?
              AND m.tombstoned_at IS NULL
            ORDER BY rank
            LIMIT 50
            """,
            (q,),
        ).fetchall()
        return {"results": [dict(r) for r in rows], "query": q}
    except Exception:
        log.exception("search_memory failed")
        return {"results": [], "query": q}
    finally:
        conn.close()


@router.get("/loops")
def list_loops() -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM karpathy_loops ORDER BY started_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        log.exception("list_loops failed")
        return []
    finally:
        conn.close()


@router.get("/audit")
def list_audit(limit: int = 100) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


@router.get("/afk/grants")
def list_afk_grants() -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        now = int(time.time())
        rows = conn.execute(
            "SELECT * FROM afk_grants WHERE expires_at > ? AND revoked_at IS NULL",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


@router.get("/schedules")
def list_schedules() -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM schedules ORDER BY next_run_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()
