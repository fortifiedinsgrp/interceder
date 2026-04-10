"""Manager Supervisor — Phase 3: memory archive + hot memory + recall tools.

The Supervisor now:
1. Opens the DB
2. Creates a Memory instance on a separate connection
3. Builds the system prompt with hot memory injection
4. Creates (or accepts an injected) ManagerSession
5. On each tick, drains inbox messages through the session with memory persistence
6. Shuts down cleanly on stop()
"""
from __future__ import annotations

import logging
import sqlite3

from interceder import config
from interceder.manager.inbox_drain import process_inbox
from interceder.manager.prompt import assemble_system_prompt
from interceder.manager.session import AgentSessionProtocol, ManagerSession
from interceder.memory import db
from interceder.memory.archive import Memory

log = logging.getLogger("interceder.manager.supervisor")


class Supervisor:
    def __init__(
        self,
        *,
        agent_session: AgentSessionProtocol | None = None,
    ) -> None:
        self._conn: sqlite3.Connection | None = None
        self._running = False
        self._injected_session = agent_session
        self._session: ManagerSession | None = None
        self._memory: Memory | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def session(self) -> ManagerSession | None:
        return self._session

    def start(self) -> None:
        log.info("supervisor starting; db=%s", config.db_path())
        self._conn = db.connect(config.db_path())
        self._memory = Memory(db.connect(config.db_path()))  # separate connection

        # Build initial system prompt with hot memory
        hot = self._memory.get_hot_memory()
        system_prompt = assemble_system_prompt(hot_items=hot)

        if self._injected_session is not None:
            self._session = ManagerSession(
                agent_session=self._injected_session,
                system_prompt=system_prompt,
            )
        else:
            self._session = self._create_real_session(system_prompt)

        self._running = True
        log.info("supervisor started")

    def _create_real_session(self, system_prompt: str) -> ManagerSession:
        """Create a real Agent SDK session on the Max subscription.

        Falls back to a no-op stub if the SDK isn't installed or auth fails.
        """
        try:
            from claude_agent_sdk import ClaudeAgentSession  # type: ignore[import-not-found]

            real_session = ClaudeAgentSession(model=config.MANAGER_MODEL)
            return ManagerSession(
                agent_session=real_session,
                system_prompt=system_prompt,
            )
        except ImportError:
            log.warning(
                "claude-agent-sdk not installed — using echo stub. "
                "Install the SDK and restart to enable real Claude."
            )
            from tests.stubs.agent_sdk_stub import StubAgentSession

            return ManagerSession(
                agent_session=StubAgentSession(model=config.MANAGER_MODEL),
                system_prompt=system_prompt,
            )

    def tick(self) -> None:
        """One pass of the main loop: drain inbox, process through session."""
        if not self._running or self._conn is None or self._session is None:
            return
        try:
            process_inbox(self._conn, self._session, limit=10, memory=self._memory)
        except Exception:
            log.exception("tick error during inbox drain")

    def stop(self) -> None:
        if not self._running and self._conn is None:
            return
        log.info("supervisor stopping")
        if self._session is not None:
            self._session.close()
            self._session = None
        if self._memory is not None:
            self._memory.close()
            self._memory = None
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._running = False
        log.info("supervisor stopped")
