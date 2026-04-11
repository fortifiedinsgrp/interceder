"""Real Claude session backed by the claude CLI subprocess.

Uses `--session-id` to create a persistent session on first use, then
`--resume` for subsequent turns so conversation history is maintained
inside Claude Code's session store — no separate API key required.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import uuid as _uuid
from pathlib import Path

log = logging.getLogger("interceder.manager.claude_session")

# launchd strips the user PATH, so probe common install locations.
_CLAUDE_SEARCH_PATHS = [
    Path.home() / ".local" / "bin" / "claude",
    Path("/usr/local/bin/claude"),
    Path("/opt/homebrew/bin/claude"),
]


def _find_claude_bin() -> str:
    """Return the absolute path to the claude CLI.

    Checks $PATH first (works in a shell), then falls back to the common
    install locations so launchd services (which run with a stripped PATH)
    can still find it.
    """
    found = shutil.which("claude")
    if found:
        return found
    for candidate in _CLAUDE_SEARCH_PATHS:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        "claude CLI not found in PATH or common locations — install Claude Code"
    )


class ClaudeAgentSession:
    """Long-lived Claude session backed by the ``claude`` CLI.

    Protocol matches the AgentSessionProtocol expected by ManagerSession.
    """

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        *,
        session_id: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.system_prompt: str = ""
        self._session_id = session_id or str(_uuid.uuid4())
        self._started = False
        self._closed = False
        self._timeout = timeout
        self._claude_bin = _find_claude_bin()

        log.info("claude session %s ready (model=%s)", self._session_id, model)

    # ------------------------------------------------------------------
    # AgentSessionProtocol
    # ------------------------------------------------------------------

    def send_message(self, message: str) -> str:
        if self._closed:
            raise RuntimeError("session is closed")

        cmd = self._start_cmd(message) if not self._started else self._resume_cmd(message)
        self._started = True

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"claude CLI timed out after {self._timeout}s"
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                f"claude exited {result.returncode}: {result.stderr[:500]}"
            )

        return result.stdout.strip()

    def close(self) -> None:
        self._closed = True
        log.info("claude session %s closed", self._session_id)

    @property
    def is_closed(self) -> bool:
        return self._closed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_cmd(self, message: str) -> list[str]:
        """First-turn command — creates the session with a fixed ID."""
        cmd = [
            self._claude_bin, "--print",
            "--model", self.model,
            "--session-id", self._session_id,
        ]
        if self.system_prompt:
            cmd.extend(["--system-prompt", self.system_prompt])
        cmd.append(message)
        return cmd

    def _resume_cmd(self, message: str) -> list[str]:
        """Subsequent turns — resume the stored session."""
        return [
            self._claude_bin, "--print",
            "--resume", self._session_id,
            message,
        ]
