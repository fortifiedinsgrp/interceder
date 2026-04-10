"""Metric runner — executes a user-provided shell command and parses a float."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger("interceder.loops.metric")


def run_metric(
    *,
    command: str,
    cwd: Path,
    timeout: int = 60,
) -> float:
    """Run a shell command and parse stdout as a float.

    Raises TimeoutError if the command exceeds `timeout` seconds.
    Raises ValueError if stdout cannot be parsed as a float.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"metric command timed out after {timeout}s") from exc

    output = result.stdout.strip()
    try:
        return float(output)
    except ValueError as exc:
        raise ValueError(
            f"metric output is not a number: {output!r}"
        ) from exc
