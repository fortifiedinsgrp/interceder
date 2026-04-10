"""Tier classification for actions.

Tier 0 = autonomous, Tier 1 = approval-gated, Tier 2 = hard-blocked.
See plan.md Security Model section for the full taxonomy.
"""
from __future__ import annotations

import re
from typing import Any

# Tier 2 — NEVER allowed
_TIER_2_PATTERNS = [
    # Destructive rm outside sandbox
    re.compile(r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|)(/|~|/Users/)"),
    # Force push to protected branches
    re.compile(r"git\s+push\s+--force.*\b(main|master|prod|production|release)\b"),
    # Any push to main/master/prod (force push is Tier 2, normal push is Tier 1)
    re.compile(r"git\s+push\s+--force.*\b(main|master|prod|production)\b"),
    # SSH directory writes
    re.compile(r"\.ssh/"),
    # Keychain access
    re.compile(r"Library/Keychains"),
    # Credential stores
    re.compile(r"\.config/gh/hosts\.yml"),
    # launchd plist modification
    re.compile(r"com\.interceder\.(gateway|manager)\.plist"),
    # Email/SMS
    re.compile(r"\b(sendmail|mail\s+-s|twilio|sns\s+publish)\b"),
    # Payment APIs
    re.compile(r"\b(stripe|plaid|ach)\b", re.IGNORECASE),
    # System paths
    re.compile(r"^/(System|private/etc)/"),
    # diskutil destructive
    re.compile(r"diskutil\s+(erase|partition|unmount)"),
]

# Tier 1 — approval-gated
_TIER_1_COMMAND_PATTERNS = [
    re.compile(r"git\s+push\b"),
    re.compile(r"git\s+merge\b"),
    re.compile(r"brew\s+install\b"),
    re.compile(r"npm\s+install\s+-g\b"),
    re.compile(r"pip\s+install\s+--user\b"),
    re.compile(r"uv\s+tool\s+install\b"),
]

# Tier 0 tools (always autonomous)
_TIER_0_TOOLS = frozenset({
    "Read", "Glob", "Grep", "Agent",
    "memory_recall", "memory_write",
    "spawn_worker_process",
    "schedule_task",
})


def classify(tool_name: str, context: dict[str, Any]) -> int:
    """Classify a tool call as Tier 0, 1, or 2."""
    # Check file path operations for Tier 2
    file_path = context.get("file_path", "")
    if file_path:
        for pattern in _TIER_2_PATTERNS:
            if pattern.search(file_path):
                return 2

    # Check command operations
    command = context.get("command", "")
    if command:
        # Tier 2 checks first
        for pattern in _TIER_2_PATTERNS:
            if pattern.search(command):
                return 2
        # Tier 1 checks
        for pattern in _TIER_1_COMMAND_PATTERNS:
            if pattern.search(command):
                return 1

    # Known Tier 0 tools
    if tool_name in _TIER_0_TOOLS:
        return 0

    # Write/Edit to files: Tier 0 if in sandbox, Tier 1 otherwise
    if tool_name in ("Edit", "Write") and file_path:
        if "/interceder-workspace/" in file_path or "/workers/" in file_path:
            return 0
        return 0  # Default to Tier 0 for allowlisted paths (Phase 13 refines)

    # Default: Tier 0
    return 0
