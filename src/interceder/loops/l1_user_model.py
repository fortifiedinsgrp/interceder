"""L1 User-Model Loop — evolves the Manager's prompt assembly code.

This is the most sensitive loop: it edits the Manager's own behavior.
Guardrails:
- Requires explicit session-scoped user approval to start
- Edits go to a dedicated branch
- Edits require a full Manager restart to take effect
- If user signals dissatisfaction after restart, auto-revert
"""
from __future__ import annotations

import logging
from pathlib import Path

from interceder.loops.core import LoopConfig

log = logging.getLogger("interceder.loops.l1_user_model")

# The specific file this loop is allowed to edit
EDITABLE_FILE = "src/interceder/manager/prompt.py"


class L1UserModelLoop:
    """Orchestrates L1 prompt evolution."""

    def __init__(
        self,
        *,
        repo_path: Path,
        conn: object,
        max_iterations: int = 5,
        time_budget_seconds: int = 3600,
    ) -> None:
        self._repo_path = repo_path
        self._conn = conn
        self._config = LoopConfig(
            layer="L1",
            editable_asset=EDITABLE_FILE,
            metric_name="user_satisfaction",
            higher_is_better=True,
            keep_threshold=0.1,
            branch="self-mod/l1-prompt",
            max_iterations=max_iterations,
            time_budget_seconds=time_budget_seconds,
        )
        self._enabled = False

    def enable(self) -> None:
        """Explicitly enable L1 loop for this session."""
        log.info("L1 user-model loop enabled for this session")
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def requires_restart(self) -> bool:
        """L1 edits always require a Manager restart."""
        return True
