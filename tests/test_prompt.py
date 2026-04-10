"""Tests for system prompt assembly with hot memory injection."""
from __future__ import annotations

from interceder.manager.prompt import assemble_system_prompt


def test_prompt_includes_identity() -> None:
    prompt = assemble_system_prompt(hot_items=[])
    assert "Interceder" in prompt
    assert "never forget" in prompt.lower() or "memory_recall" in prompt


def test_prompt_includes_hot_memory() -> None:
    hot_items = [
        {"slot": "pinned_facts", "content": "user prefers tabs"},
        {"slot": "active_task", "content": "working on dashboard refactor"},
    ]
    prompt = assemble_system_prompt(hot_items=hot_items)
    assert "user prefers tabs" in prompt
    assert "dashboard refactor" in prompt


def test_prompt_without_hot_memory() -> None:
    prompt = assemble_system_prompt(hot_items=[])
    assert "Interceder" in prompt
    # Should still have the core identity and discipline
    assert len(prompt) > 100
