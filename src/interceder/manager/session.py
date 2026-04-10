"""Wrapper around the Claude Agent SDK session.

Provides a clean interface for the Supervisor to send turns and manage
the session lifecycle. The real Agent SDK session is injected — tests
use StubAgentSession, production uses the real SDK.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

log = logging.getLogger("interceder.manager.session")


class AgentSessionProtocol(Protocol):
    """Minimal interface the Manager needs from any Agent SDK session."""

    model: str
    system_prompt: str

    def send_message(self, message: str) -> str: ...
    def close(self) -> None: ...

    @property
    def is_closed(self) -> bool: ...


class ManagerSession:
    """Thin wrapper that tracks turns and provides lifecycle management."""

    def __init__(
        self,
        agent_session: AgentSessionProtocol,
        *,
        system_prompt: str = "",
    ) -> None:
        self._session = agent_session
        if system_prompt:
            self._session.system_prompt = system_prompt
        self._turn_count = 0
        self._closed = False

    def send(self, message: str) -> str:
        log.info("sending turn %d (%d chars)", self._turn_count + 1, len(message))
        reply = self._session.send_message(message)
        self._turn_count += 1
        log.info("received reply (%d chars)", len(reply))
        return reply

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @property
    def is_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if not self._closed:
            self._session.close()
            self._closed = True
            log.info("session closed after %d turns", self._turn_count)
