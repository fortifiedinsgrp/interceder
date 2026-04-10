"""Custom tool definitions for the Manager session.

These are registered on the Agent SDK session so the Manager can call them.
Phase 3: memory_recall and memory_write.
Later phases add: spawn_worker_process, approve_or_queue, schedule_task,
start_karpathy_loop, self_modify.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from interceder.memory.archive import Memory

log = logging.getLogger("interceder.manager.tools")


def memory_recall(
    memory: Memory,
    *,
    query: str,
    limit: int = 10,
) -> str:
    """Search the memory archive. Returns JSON array of matching messages."""
    results = memory.recall(query, limit=limit)
    if not results:
        return json.dumps({"results": [], "message": "No matches found."})
    return json.dumps({"results": results}, default=str)


def memory_write(
    memory: Memory,
    *,
    entity_name: str,
    entity_kind: str,
    claim: str,
    confidence: float = 1.0,
) -> str:
    """Write a structured fact to the memory archive."""
    eid = memory.add_entity(name=entity_name, kind=entity_kind)
    fid = memory.add_fact(entity_id=eid, claim=claim, confidence=confidence)
    return json.dumps({"entity_id": eid, "fact_id": fid, "status": "written"})
