# Install & Update Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `deploy/update.sh` (pull + rebuild + restart) and a State 3 detection block to `CLAUDE.md` so a remote machine with a stale install can be repaired in one command or through a guided Claude Code session.

**Architecture:** `update.sh` is a self-contained bash script modelled on `install.sh`; it pulls the repo, syncs deps, rebuilds the webapp, and restarts the two launchd services. `CLAUDE.md` gains a new detection state between the current states 2 and 3 that checks for pending git commits and the echo-stub warning in the manager log.

**Tech Stack:** bash, git, uv, npm, launchctl, curl

---

## File Map

| File | Change |
|---|---|
| `deploy/update.sh` | New — pull, sync, build, restart, verify |
| `CLAUDE.md` | Modify — insert State 3 detection block, renumber old State 3 → 4 |
| `tests/test_update_script.py` | New — sandbox tests mirroring `test_install_script.py` |

---

### Task 1: Write failing tests for `update.sh`

**Files:**
- Create: `tests/test_update_script.py`

- [ ] **Step 1: Create the test file**

```python
"""End-to-end tests for deploy/update.sh in a sandboxed HOME."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATE_SH = REPO_ROOT / "deploy" / "update.sh"


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    fake = tmp_path / "fake-home"
    (fake / "Library" / "Application Support").mkdir(parents=True)
    (fake / "Library" / "LaunchAgents").mkdir(parents=True)
    return fake


def _run_update(fake_home: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "HOME": str(fake_home),
        "INTERCEDER_SKIP_LAUNCHD": "1",
        "INTERCEDER_SKIP_WEBAPP": "1",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(UPDATE_SH)],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_update_script_exists() -> None:
    assert UPDATE_SH.exists(), "deploy/update.sh does not exist"


def test_update_runs_and_exits_zero(fake_home: Path) -> None:
    result = _run_update(fake_home)
    assert result.returncode == 0, (
        f"update.sh failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_update_logs_steps(fake_home: Path) -> None:
    result = _run_update(fake_home)
    assert result.returncode == 0
    assert "[update]" in result.stdout


def test_update_is_idempotent(fake_home: Path) -> None:
    first = _run_update(fake_home)
    assert first.returncode == 0, first.stderr
    second = _run_update(fake_home)
    assert second.returncode == 0, second.stderr
```

- [ ] **Step 2: Run tests to confirm they fail (script doesn't exist yet)**

```bash
uv run pytest tests/test_update_script.py -v
```

Expected: `test_update_script_exists` FAILS with "deploy/update.sh does not exist". Others may error. That's the signal to proceed.

---

### Task 2: Write `deploy/update.sh`

**Files:**
- Create: `deploy/update.sh`

- [ ] **Step 1: Create the script**

```bash
#!/usr/bin/env bash
# deploy/update.sh — pull latest code, rebuild, and restart Interceder services.
#
# Opt-out env vars:
#   INTERCEDER_SKIP_WEBAPP=1    — skip npm build (when Node isn't available)
#   INTERCEDER_SKIP_LAUNCHD=1   — skip service restart (for CI / testing)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
INTERCEDER_HOME="${HOME}/Library/Application Support/Interceder"

log() { printf '[update] %s\n' "$*"; }
die() { printf '[update] ERROR: %s\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------------
# 1. Pull latest code
# --------------------------------------------------------------------
log "pulling latest code from origin"
git -C "${REPO_ROOT}" pull --ff-only

# --------------------------------------------------------------------
# 2. Sync Python dependencies
# --------------------------------------------------------------------
log "syncing Python dependencies"
(cd "${REPO_ROOT}" && uv sync)

# --------------------------------------------------------------------
# 3. Rebuild webapp (optional)
# --------------------------------------------------------------------
if [[ "${INTERCEDER_SKIP_WEBAPP:-0}" == "1" ]]; then
    log "skipping webapp build (INTERCEDER_SKIP_WEBAPP=1)"
elif command -v npm >/dev/null 2>&1; then
    log "rebuilding webapp"
    (cd "${REPO_ROOT}/webapp" && npm install && npm run build)
else
    log "WARNING: npm not found — skipping webapp build"
fi

# --------------------------------------------------------------------
# 4. Restart launchd services
# --------------------------------------------------------------------
if [[ "${INTERCEDER_SKIP_LAUNCHD:-0}" == "1" ]]; then
    log "skipping service restart (INTERCEDER_SKIP_LAUNCHD=1)"
else
    for name in gateway manager; do
        plist="${LAUNCH_AGENTS}/com.interceder.${name}.plist"
        if [[ -f "${plist}" ]]; then
            log "restarting com.interceder.${name}"
            launchctl unload "${plist}" 2>/dev/null || true
            launchctl load "${plist}"
        else
            log "WARNING: ${plist} not found — skipping com.interceder.${name}"
        fi
    done

    # --------------------------------------------------------------------
    # 5. Verify
    # --------------------------------------------------------------------
    sleep 2
    log "verifying gateway health"
    health="$(curl -sf http://127.0.0.1:7878/health 2>/dev/null || echo '{}')"
    if [[ "${health}" != *'"status":"ok"'* ]]; then
        die "gateway health check failed: ${health}"
    fi

    if grep -q "echo stub" "${INTERCEDER_HOME}/logs/manager.err.log" 2>/dev/null; then
        die "manager is still in echo stub mode after update — check ${INTERCEDER_HOME}/logs/manager.err.log"
    fi

    log "all checks passed"
fi

log "update complete"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x deploy/update.sh
```

- [ ] **Step 3: Run the tests**

```bash
uv run pytest tests/test_update_script.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add deploy/update.sh tests/test_update_script.py
git commit -m "feat: add deploy/update.sh with idempotent pull/rebuild/restart"
```

---

### Task 3: Add State 3 detection to CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:9-13` (the "Detecting Install State" block)

- [ ] **Step 1: Replace the detection block**

Find this exact block in `CLAUDE.md`:

```
When starting a session in this repo, check installation state:

1. If `~/Library/Application Support/Interceder/` does not exist → **offer to install**: "Interceder isn't installed yet. Want me to walk you through the setup?"
2. If it exists but services aren't running (`launchctl list | grep interceder` returns nothing) → **offer to repair**: "Interceder is installed but the services aren't running. Want me to start them?"
3. If everything is running → operate normally.
```

Replace with:

```
When starting a session in this repo, check installation state:

1. If `~/Library/Application Support/Interceder/` does not exist → **offer to install**: "Interceder isn't installed yet. Want me to walk you through the setup?"
2. If it exists but services aren't running (`launchctl list | grep interceder` returns nothing) → **offer to repair**: "Interceder is installed but the services aren't running. Want me to start them?"
3. If services are running but either of these is true → **offer to update**: "Interceder is running but there's an update available (or the manager is in fallback/echo mode). Want me to update and restart?"
   - `git fetch origin --quiet 2>/dev/null; git rev-list HEAD..origin/main --count` returns a number > 0 (commits to pull)
   - `grep -q "echo stub" ~/Library/Application\ Support/Interceder/logs/manager.err.log 2>/dev/null` succeeds (manager fell back to echo stub)

   If accepted, run: `bash <repo_root>/deploy/update.sh` (where `<repo_root>` is the current working directory).
   If declined, operate normally.

4. If everything is running and up to date → operate normally.
```

- [ ] **Step 2: Verify the edit looks correct**

```bash
grep -A 20 "Detecting Install State" CLAUDE.md
```

Expected: four numbered states, State 3 contains "echo stub" and "update".

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add State 3 update detection to CLAUDE.md install runbook"
```

---

## Self-Review

**Spec coverage:**
- `deploy/update.sh` → Task 2 ✓
- CLAUDE.md State 3 detection → Task 3 ✓
- Tests → Task 1 + Task 2 ✓
- Opt-out env vars (`INTERCEDER_SKIP_WEBAPP`, `INTERCEDER_SKIP_LAUNCHD`) → Task 2 ✓

**Placeholder scan:** None found.

**Type consistency:** Only bash and markdown — no type mismatches possible.
