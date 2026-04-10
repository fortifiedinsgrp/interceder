"""Tool registry — metadata for all custom tools.

Each tool has a name, description, tier, and implementation reference.
The Manager uses this to present tools to the Agent SDK session.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolDef:
    name: str
    description: str
    tier: int  # 0 = auto, 1 = approval, 2 = blocked
    handler: Callable[..., str] | None = None
    cost_tracking: bool = False


_REGISTRY: dict[str, ToolDef] = {}


def register(tool: ToolDef) -> None:
    _REGISTRY[tool.name] = tool


def get(name: str) -> ToolDef | None:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolDef]:
    return list(_REGISTRY.values())
