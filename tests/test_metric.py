"""Tests for the metric runner — executes user-provided metric commands."""
from __future__ import annotations

from pathlib import Path

import pytest

from interceder.loops.metric import run_metric


def test_run_shell_metric(tmp_path: Path) -> None:
    script = tmp_path / "metric.sh"
    script.write_text("#!/bin/bash\necho 3.14")
    script.chmod(0o755)
    result = run_metric(command=f"bash {script}", cwd=tmp_path, timeout=5)
    assert abs(result - 3.14) < 0.01


def test_run_python_metric(tmp_path: Path) -> None:
    script = tmp_path / "metric.py"
    script.write_text("print(42.0)")
    result = run_metric(command=f"python {script}", cwd=tmp_path, timeout=5)
    assert result == 42.0


def test_run_metric_timeout(tmp_path: Path) -> None:
    with pytest.raises(TimeoutError):
        run_metric(command="sleep 10", cwd=tmp_path, timeout=1)


def test_run_metric_bad_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a number"):
        run_metric(command="echo 'not a number'", cwd=tmp_path, timeout=5)
