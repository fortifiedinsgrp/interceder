"""Deterministic stub for the Claude Agent SDK session.

Used in tests to avoid hitting real Claude. Returns scripted responses
based on a configurable callback or a default echo pattern.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class StubTurn:
    user_message: str
    response: str


@dataclass
class StubAgentSession:
    """Drop-in replacement for the real Agent SDK session."""

    model: str = "claude-opus-4-6"
    system_prompt: str = ""
    turns: list[StubTurn] = field(default_factory=list)
    _response_fn: Callable[[str], str] | None = None
    _closed: bool = False

    def set_response_fn(self, fn: Callable[[str], str]) -> None:
        self._response_fn = fn

    def send_message(self, message: str) -> str:
        if self._closed:
            raise RuntimeError("session is closed")
        if self._response_fn:
            response = self._response_fn(message)
        else:
            response = f"Echo: {message}"
        self.turns.append(StubTurn(user_message=message, response=response))
        return response

    def close(self) -> None:
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed
