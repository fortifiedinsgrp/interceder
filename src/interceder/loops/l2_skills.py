"""L2 Skills loop — refines skills based on post-task reflection.

The L2 loop is triggered lazily after task completion (via the task_reflection
skill), not run continuously. When enough self-grade events accumulate for
a skill, an iteration edits the skill file and evaluates the result.
"""
from __future__ import annotations

import logging

from interceder.loops.core import KarpathyLoop, LoopConfig

log = logging.getLogger("interceder.loops.l2_skills")


class L2SkillsLoop:
    """Orchestrates skill refinement iterations.

    Phase 7 provides the scaffolding. The actual skill-editing logic
    delegates to Claude Code's writing-skills meta-skill via the Agent SDK.
    """

    def __init__(
        self,
        *,
        skill_dir: str,
        conn: object,
    ) -> None:
        self._skill_dir = skill_dir
        self._conn = conn

    def should_iterate(self, skill_name: str, grade_count: int) -> bool:
        """Check if enough grades have accumulated to warrant an iteration."""
        return grade_count >= 5  # configurable threshold

    def record_grade(
        self,
        *,
        skill_name: str,
        task_id: str,
        score: int,
        notes: str,
    ) -> None:
        """Record a self-grade for a skill invocation."""
        log.info(
            "skill grade: %s score=%d for task %s",
            skill_name, score, task_id,
        )
        # Persisted via Memory.add_fact in the Supervisor
