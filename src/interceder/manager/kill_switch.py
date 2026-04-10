"""Kill switches — global and per-workflow.

Global kill: halts all Workers, pauses all Karpathy loops, stops all
scheduled tasks. Manager stays online to explain what happened.

Per-workflow: pauses a specific loop or kills a specific worker.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger("interceder.manager.kill_switch")


class KillSwitch:
    def __init__(self) -> None:
        self._killed = False
        self._kill_reason = ""
        self._killed_at: float | None = None
        self._killed_workflows: dict[str, str] = {}  # id → reason

    def kill_all(self, *, reason: str) -> None:
        self._killed = True
        self._kill_reason = reason
        self._killed_at = time.time()
        log.warning("GLOBAL KILL SWITCH ACTIVATED: %s", reason)

    def resume(self) -> None:
        self._killed = False
        self._kill_reason = ""
        self._killed_at = None
        log.info("global kill switch deactivated")

    def is_killed(self) -> bool:
        return self._killed

    def kill_reason(self) -> str:
        return self._kill_reason

    def kill_workflow(self, workflow_id: str, *, reason: str) -> None:
        self._killed_workflows[workflow_id] = reason
        log.warning("workflow %s killed: %s", workflow_id, reason)

    def is_workflow_killed(self, workflow_id: str) -> bool:
        return workflow_id in self._killed_workflows

    def resume_workflow(self, workflow_id: str) -> None:
        self._killed_workflows.pop(workflow_id, None)
