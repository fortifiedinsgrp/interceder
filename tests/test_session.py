"""Tests for the Manager's Agent SDK session wrapper."""
from __future__ import annotations

import pytest

from tests.stubs.agent_sdk_stub import StubAgentSession
from interceder.manager.session import ManagerSession


def test_session_send_and_receive() -> None:
    stub = StubAgentSession()
    session = ManagerSession(agent_session=stub)
    reply = session.send("hello")
    assert reply == "Echo: hello"


def test_session_tracks_turn_count() -> None:
    stub = StubAgentSession()
    session = ManagerSession(agent_session=stub)
    session.send("one")
    session.send("two")
    assert session.turn_count == 2


def test_session_close() -> None:
    stub = StubAgentSession()
    session = ManagerSession(agent_session=stub)
    session.send("hi")
    session.close()
    assert session.is_closed


def test_session_custom_system_prompt() -> None:
    stub = StubAgentSession()
    session = ManagerSession(
        agent_session=stub,
        system_prompt="You are Interceder."
    )
    assert stub.system_prompt == "You are Interceder."
