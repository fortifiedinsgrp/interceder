# Curl Install + AI-Guided Setup + Documentation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Interceder installable via `curl | bash` from GitHub, with Claude Code driving the rest of the install interactively using in-repo documentation.

**Architecture:** A thin bootstrap script (`deploy/bootstrap.sh`) clones the repo and launches Claude Code. `CLAUDE.md` contains an install runbook Claude Code follows step-by-step. Seven docs in `docs/` provide deep reference material for answering questions and troubleshooting. `README.md` is the GitHub landing page.

**Tech Stack:** Bash (bootstrap script), Markdown (all docs + CLAUDE.md + README)

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `deploy/bootstrap.sh` | Thin curl-able bootstrap: check git+claude, clone repo, launch claude |
| Create | `CLAUDE.md` | Project guidance + install runbook for Claude Code |
| Create | `README.md` | GitHub landing page with quick start |
| Create | `docs/install-guide.md` | Detailed prereqs, manual install steps, env vars |
| Create | `docs/architecture.md` | System design, message flow, database schema |
| Create | `docs/configuration.md` | config.toml options, Keychain secrets, env overrides |
| Create | `docs/slack-setup.md` | Slack app creation, tokens, Socket Mode |
| Create | `docs/webapp.md` | Building/serving the React webapp, WebSocket API |
| Create | `docs/troubleshooting.md` | Common errors, log locations, restart procedures |
| Create | `docs/faq.md` | Frequently asked questions |
| Create | `docs/launchd.md` | Daemon management, plist templates, start/stop |
| Create | `tests/test_bootstrap_script.py` | Tests for bootstrap.sh |

---

### Task 1: Bootstrap Script

**Files:**
- Create: `deploy/bootstrap.sh`
- Create: `tests/test_bootstrap_script.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_bootstrap_script.py`:

```python
"""Tests for deploy/bootstrap.sh — validates the thin curl-able bootstrap."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SH = REPO_ROOT / "deploy" / "bootstrap.sh"


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A temp directory to use as clone target."""
    return tmp_path / "clone-target"


def _run_bootstrap(
    sandbox: Path,
    *,
    skip_clone: bool = False,
    skip_launch: bool = True,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "INTERCEDER_CLONE_DIR": str(sandbox),
        # Always skip launching claude in tests
        "INTERCEDER_SKIP_LAUNCH": "1" if skip_launch else "0",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(BOOTSTRAP_SH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_bootstrap_script_exists() -> None:
    assert BOOTSTRAP_SH.exists()
    assert BOOTSTRAP_SH.stat().st_mode & 0o111, "bootstrap.sh must be executable"


def test_bootstrap_clones_repo(sandbox: Path) -> None:
    result = _run_bootstrap(sandbox)
    assert result.returncode == 0, (
        f"bootstrap.sh failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert (sandbox / ".git").is_dir(), "repo should be cloned"
    assert (sandbox / "pyproject.toml").exists(), "repo contents should exist"


def test_bootstrap_pulls_if_already_cloned(sandbox: Path) -> None:
    # First run clones
    first = _run_bootstrap(sandbox)
    assert first.returncode == 0, first.stderr
    # Second run should pull, not fail
    second = _run_bootstrap(sandbox)
    assert second.returncode == 0, second.stderr
    assert "already exists" in second.stdout.lower() or "pulling" in second.stdout.lower()


def test_bootstrap_fails_without_git(sandbox: Path, tmp_path: Path) -> None:
    # Create an empty bin dir with no git
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    result = _run_bootstrap(sandbox, extra_env={"PATH": str(empty_bin)})
    assert result.returncode != 0
    assert "git" in result.stderr.lower() or "git" in result.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/marcsinger/Downloads/interceder && uv run pytest tests/test_bootstrap_script.py -v`
Expected: FAIL — `bootstrap.sh` does not exist yet.

- [ ] **Step 3: Write the bootstrap script**

Create `deploy/bootstrap.sh`:

```bash
#!/usr/bin/env bash
# deploy/bootstrap.sh — curl-able bootstrap for Interceder.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/fortifiedinsgrp/interceder/main/deploy/bootstrap.sh | bash
#
# Env vars:
#   INTERCEDER_CLONE_DIR  — where to clone (default: ~/interceder)
#   INTERCEDER_SKIP_LAUNCH — set to 1 to skip launching Claude Code (for tests)

set -euo pipefail

CLONE_DIR="${INTERCEDER_CLONE_DIR:-${HOME}/interceder}"
REPO_URL="https://github.com/fortifiedinsgrp/interceder.git"

log()  { printf '[interceder] %s\n' "$*"; }
die()  { printf '[interceder] ERROR: %s\n' "$*" >&2; exit 1; }

# ------------------------------------------------------------------
# 1. Check bare minimum prerequisites
# ------------------------------------------------------------------
command -v git >/dev/null 2>&1 || die "git is not installed. Install it from https://git-scm.com/ or via: xcode-select --install"
command -v claude >/dev/null 2>&1 || die "Claude Code CLI is not installed. Install it from https://claude.ai/claude-code"

# ------------------------------------------------------------------
# 2. Clone or update the repo
# ------------------------------------------------------------------
if [[ -d "${CLONE_DIR}/.git" ]]; then
    log "repo already exists at ${CLONE_DIR} — pulling latest"
    git -C "${CLONE_DIR}" pull --ff-only || log "WARNING: pull failed — continuing with existing checkout"
else
    log "cloning interceder to ${CLONE_DIR}"
    git clone "${REPO_URL}" "${CLONE_DIR}"
fi

# ------------------------------------------------------------------
# 3. Launch Claude Code
# ------------------------------------------------------------------
if [[ "${INTERCEDER_SKIP_LAUNCH:-0}" == "1" ]]; then
    log "skipping Claude Code launch (INTERCEDER_SKIP_LAUNCH=1)"
    log "done — repo is at ${CLONE_DIR}"
    exit 0
fi

log "launching Claude Code in ${CLONE_DIR}..."
log "Claude Code will read CLAUDE.md and guide you through the rest of the installation."
cd "${CLONE_DIR}" && exec claude
```

- [ ] **Step 4: Make it executable**

Run: `chmod +x deploy/bootstrap.sh`

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/marcsinger/Downloads/interceder && uv run pytest tests/test_bootstrap_script.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add deploy/bootstrap.sh tests/test_bootstrap_script.py
git commit -m "feat: add curl-able bootstrap script with tests"
```

---

### Task 2: CLAUDE.md — Install Runbook

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write CLAUDE.md**

Create `CLAUDE.md` at the repo root:

```markdown
# Interceder

Interceder is a remote Claude Code harness — a persistent, conversational AI assistant that runs on a dedicated Mac and is accessible remotely from Slack and a web app. It consists of two services: a Gateway (FastAPI + Slack Socket Mode) and a Manager Supervisor (long-lived Claude Opus session).

## Installation

### Detecting Install State

When starting a session in this repo, check installation state:

1. If `~/Library/Application Support/Interceder/` does not exist → **offer to install**: "Interceder isn't installed yet. Want me to walk you through the setup?"
2. If it exists but services aren't running (`launchctl list | grep interceder` returns nothing) → **offer to repair**: "Interceder is installed but the services aren't running. Want me to start them?"
3. If everything is running → operate normally.

### Install Runbook

When the user accepts the install offer, follow these steps in order. Explain what each step does. If a step fails, diagnose the error and help fix it before continuing.

#### Step 1: Check Prerequisites

Run each check and report the result:

- **macOS**: `uname -s` must return `Darwin`. This is macOS-only — launchd and Keychain are required.
- **Python 3.12+**: `python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"` must return `3.12` or `3.13`. Python runs the Gateway and Manager services. If missing: `brew install python@3.12`
- **uv**: `uv --version`. The fast Python package manager that manages dependencies. If missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Tailscale** (optional): `tailscale --version`. Provides secure remote access to the webapp. Not required for local-only use. If missing: `brew install tailscale`

#### Step 2: Install Python Dependencies

```bash
cd <repo_root>
uv sync
```

This installs all Python dependencies (FastAPI, Slack SDK, Pydantic, etc.) into a local `.venv/`.

#### Step 3: Create Directory Structure

```bash
mkdir -p ~/Library/Application\ Support/Interceder/{db,blobs,claude-config/skills,claude-config/agents,claude-config/plugins,workers,logs}
```

These directories store:
- `db/` — SQLite database (`memory.sqlite`)
- `blobs/` — Content-addressed attachment storage
- `claude-config/` — Claude Code configuration for the Manager
- `workers/` — Worker subprocess transcripts
- `logs/` — Service log files

#### Step 4: Generate config.toml

Ask the user:
- "What user_id would you like? (default: 'me')"
- "What quiet hours do you want? (default: 23:00-07:00)"

If `~/Library/Application Support/Interceder/config.toml` already exists, skip this step and tell the user.

Write to `~/Library/Application Support/Interceder/config.toml`:

```toml
# Interceder configuration. Non-secret values only.
# Secrets live in the macOS Keychain under service name "Interceder".

[general]
user_id = "<user's choice>"

[allowlist]
# Add repo roots here, e.g. paths = ["~/code/repoA", "~/code/repoB"]
paths = []

[quiet_hours]
start = "<user's choice, default 23:00>"
end   = "<user's choice, default 07:00>"
timezone = "local"

[proactive.rate_limit_seconds]
worker_done       = 30
approval          = 0
failure           = 0
idle_reflection   = 900
opportunistic     = 3600

[secrets]
# Keychain entry names (not values).
slack_bot_token = "interceder/slack_bot_token"
slack_app_token = "interceder/slack_app_token"
webapp_jwt_key  = "interceder/webapp_jwt_key"
veo_api_key     = "interceder/veo_api_key"
gemini_api_key  = "interceder/gemini_api_key"
```

#### Step 5: Run Database Migrations

```bash
uv run python -m interceder migrate
```

This creates `memory.sqlite` with 6 schema migrations: inbox/outbox queues, message archive with full-text search, worker tracking, approval queues, Karpathy loop tables, and the scheduler.

#### Step 6: Seed Claude Config

If `~/Library/Application Support/Interceder/claude-config/settings.json` does not exist:

```bash
cat > ~/Library/Application\ Support/Interceder/claude-config/settings.json << 'JSON'
{
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "name": "interceder",
    "description": "Interceder harness Claude config",
    "permissions": {
        "allow": [],
        "deny": []
    },
    "skills": {
        "directories": ["./skills"]
    }
}
JSON
```

If `~/Library/Application Support/Interceder/claude-config/skills/.git` does not exist:

```bash
cd ~/Library/Application\ Support/Interceder/claude-config/skills
git init -q
git -c user.email=interceder@localhost -c user.name=Interceder commit --allow-empty -q -m "chore: seed Interceder skill library"
```

#### Step 7: Build the Webapp (optional)

Check if npm is available: `command -v npm`. If not, skip this step and tell the user: "npm not found — skipping webapp build. You can install Node.js later and run `cd webapp && npm install && npm run build`."

If npm is available:

```bash
cd <repo_root>/webapp
npm install
npm run build
```

The webapp provides a browser-based UI for chatting with the Manager, viewing workers, approving actions, and searching memory.

#### Step 8: Install launchd Services

```bash
REPO_ROOT="<absolute path to this repo>"
INTERCEDER_HOME="$HOME/Library/Application Support/Interceder"
UV_BIN="$(command -v uv)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

mkdir -p "$LAUNCH_AGENTS"

for name in gateway manager; do
    sed \
        -e "s|__INTERCEDER_HOME__|${INTERCEDER_HOME}|g" \
        -e "s|__INTERCEDER_REPO__|${REPO_ROOT}|g" \
        -e "s|__INTERCEDER_UV_BIN__|${UV_BIN}|g" \
        "${REPO_ROOT}/deploy/com.interceder.${name}.plist" \
        > "${LAUNCH_AGENTS}/com.interceder.${name}.plist"

    launchctl unload "${LAUNCH_AGENTS}/com.interceder.${name}.plist" 2>/dev/null || true
    launchctl load "${LAUNCH_AGENTS}/com.interceder.${name}.plist"
done
```

Explain: "The Gateway handles incoming messages from Slack and the webapp. The Manager is the AI brain that processes messages and spawns workers."

#### Step 9: Verify

```bash
launchctl list | grep interceder
```

Both `com.interceder.gateway` and `com.interceder.manager` should appear.

```bash
curl -s http://127.0.0.1:7878/health
```

Should return `{"status":"ok","service":"gateway"}`.

If either check fails, read the logs:
- `~/Library/Application Support/Interceder/logs/gateway.log`
- `~/Library/Application Support/Interceder/logs/gateway.err.log`
- `~/Library/Application Support/Interceder/logs/manager.log`
- `~/Library/Application Support/Interceder/logs/manager.err.log`

### Post-Install

After a successful install, tell the user:
- "Interceder is installed and running."
- "Slack integration is optional — ask me to 'configure Slack' whenever you're ready. See `docs/slack-setup.md` for details."
- "The webapp is at http://127.0.0.1:7878 (or via Tailscale from other devices)."
- "For troubleshooting, see `docs/troubleshooting.md`."

## Development

- **Language:** Python 3.12+, TypeScript (webapp)
- **Package manager:** uv (Python), npm (webapp)
- **Tests:** `uv run pytest` — runs the full test suite
- **Code style:** Standard Python conventions, type hints throughout
- **Project structure:** `src/interceder/` is the main package, `tests/` mirrors it
- **Database:** SQLite with WAL mode at `~/Library/Application Support/Interceder/db/memory.sqlite`
- **Key modules:**
  - `gateway/` — FastAPI server, Slack Socket Mode, WebSocket, REST API
  - `manager/` — Supervisor, session management, inbox/outbox processing
  - `worker/` — Subprocess spawning, event streaming, sandboxing
  - `approval/` — Permission tiers (0=auto, 1=approval, 2=blocked)
  - `memory/` — SQLite helpers, archive, migration runner
  - `loops/` — Karpathy self-improvement loops (L1/L2/L3)
  - `scheduler/` — Cron-like recurring tasks
  - `tools/` — Third-party integrations (image/video gen, cost tracking)

## Documentation

For deeper information, see the `docs/` directory:

| Doc | What it covers |
|-----|---------------|
| [docs/install-guide.md](docs/install-guide.md) | Prerequisites, manual install, env vars |
| [docs/architecture.md](docs/architecture.md) | System design, message flow, database |
| [docs/configuration.md](docs/configuration.md) | config.toml, Keychain, env overrides |
| [docs/slack-setup.md](docs/slack-setup.md) | Slack app setup (post-install) |
| [docs/webapp.md](docs/webapp.md) | React webapp build and usage |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common errors, logs, restart |
| [docs/faq.md](docs/faq.md) | Frequently asked questions |
| [docs/launchd.md](docs/launchd.md) | Daemon management |
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with install runbook and project guidance"
```

---

### Task 3: README.md — GitHub Landing Page

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Create `README.md` at the repo root:

```markdown
# Interceder

A persistent, conversational AI assistant that runs on a dedicated Mac — accessible remotely from Slack and a web app. Drive your "home" Claude Code from any device, anywhere.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/fortifiedinsgrp/interceder/main/deploy/bootstrap.sh | bash
```

This clones the repo and launches Claude Code, which walks you through the rest of the installation.

### Prerequisites

- **macOS** (required — uses launchd and Keychain)
- **[Claude Code](https://claude.ai/claude-code)** CLI
- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **[Tailscale](https://tailscale.com/)** — for remote access (optional for local-only use)

### Manual Install (without Claude Code)

```bash
git clone https://github.com/fortifiedinsgrp/interceder.git ~/interceder
cd ~/interceder
bash deploy/install.sh
```

## How It Works

Interceder runs two persistent services on your Mac:

| Service | What it does |
|---------|-------------|
| **Gateway** | FastAPI server on port 7878 + Slack Socket Mode listener. Receives messages from Slack and the webapp, queues them in SQLite for the Manager. |
| **Manager** | A long-lived Claude Opus session (via Claude Agent SDK). Processes messages, manages persistent memory, spawns Worker subagents for tasks, and delivers responses. |

```
Slack / webapp
      ↓
  Gateway (enqueue → inbox table)
      ↓
  Manager Supervisor (drain inbox → Claude session → enqueue outbox)
      ↓
  Gateway (drain outbox → Slack / webapp delivery)
```

### Workers

The Manager spawns ephemeral Worker subagents (Claude Sonnet) for concrete tasks — implementing features, running experiments, debugging. Workers stream status updates back to the Manager, which decides what to surface to you.

### Memory

Interceder remembers everything. All messages, tool calls, worker transcripts, and decisions are archived in SQLite with full-text search (FTS5). An LLM-driven extraction pass distills facts, entities, and reflections for structured recall.

### Permissions

Actions are classified into three tiers:
- **Tier 0 (autonomous)** — reads, tests, local builds, memory writes, spawning workers
- **Tier 1 (approval-gated)** — git push, merging PRs, installing packages, external API calls
- **Tier 2 (hard-blocked)** — destructive operations, credential access, system modifications

## Documentation

| Doc | Description |
|-----|-------------|
| [Install Guide](docs/install-guide.md) | Detailed prerequisites and manual install steps |
| [Architecture](docs/architecture.md) | System design, message flow, database schema |
| [Configuration](docs/configuration.md) | config.toml options, Keychain secrets, env vars |
| [Slack Setup](docs/slack-setup.md) | Creating a Slack app and connecting it |
| [Web App](docs/webapp.md) | Building and using the React webapp |
| [Troubleshooting](docs/troubleshooting.md) | Common errors and fixes |
| [FAQ](docs/faq.md) | Frequently asked questions |
| [Launchd Services](docs/launchd.md) | Managing the background daemons |

## Optional: Slack Integration

After installation, ask Claude Code to "configure Slack" — it will walk you through creating a Slack app and connecting it. See [docs/slack-setup.md](docs/slack-setup.md) for the full guide.

## Updating

```bash
cd ~/interceder
git pull
uv sync
uv run python -m interceder migrate
```

Then restart services:

```bash
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl unload ~/Library/LaunchAgents/com.interceder.manager.plist
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.manager.plist
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README.md with quick start and project overview"
```

---

### Task 4: docs/install-guide.md

**Files:**
- Create: `docs/install-guide.md`

- [ ] **Step 1: Write the doc**

Create `docs/install-guide.md`:

```markdown
# Install Guide

Complete installation instructions for Interceder. The recommended path is the [Quick Start](#quick-start) curl command, which launches Claude Code to guide you interactively. This document covers manual installation for reference.

## Quick Start (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/fortifiedinsgrp/interceder/main/deploy/bootstrap.sh | bash
```

This clones the repo and launches Claude Code, which walks you through every step below.

## Prerequisites

| Requirement | Minimum Version | Check Command | Install Command |
|------------|----------------|---------------|-----------------|
| macOS | Any supported | `uname -s` → `Darwin` | N/A (macOS only) |
| Python | 3.12 | `python3 --version` | `brew install python@3.12` |
| git | Any | `git --version` | `xcode-select --install` |
| uv | Any | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Claude Code CLI | Any | `claude --version` | See https://claude.ai/claude-code |
| Tailscale | Any (optional) | `tailscale --version` | `brew install tailscale` |
| Node.js + npm | 18+ (optional) | `node --version` | `brew install node` |

### Why each prerequisite

- **Python 3.12+** — Interceder's backend (Gateway + Manager) is Python. Uses `match` statements and other 3.12 features.
- **uv** — Manages Python dependencies. Much faster than pip. Creates a `.venv/` in the repo.
- **git** — Clones the repo, manages the skills library.
- **Claude Code** — The AI that drives the installation and powers the Manager session.
- **Tailscale** — Optional. Provides encrypted network access so you can reach the webapp from other devices. Not needed for local-only use.
- **Node.js** — Optional. Only needed to build the web dashboard.

## Manual Install Steps

### 1. Clone the repository

```bash
git clone https://github.com/fortifiedinsgrp/interceder.git ~/interceder
cd ~/interceder
```

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Create the data directory

```bash
mkdir -p ~/Library/Application\ Support/Interceder/{db,blobs,claude-config/skills,claude-config/agents,claude-config/plugins,workers,logs}
```

### 4. Generate config.toml

```bash
bash deploy/install.sh
```

Or create `~/Library/Application Support/Interceder/config.toml` manually — see [Configuration](configuration.md) for all options.

### 5. Run database migrations

```bash
uv run python -m interceder migrate
```

### 6. Build the webapp (optional)

```bash
cd webapp && npm install && npm run build
```

### 7. Install launchd services

```bash
bash deploy/install.sh
```

Or run the install script which handles steps 3-7 automatically:

```bash
bash deploy/install.sh
```

### 8. Verify

```bash
# Check services are running
launchctl list | grep interceder

# Check Gateway health
curl -s http://127.0.0.1:7878/health
# Expected: {"status":"ok","service":"gateway"}
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `INTERCEDER_HOME` | `~/Library/Application Support/Interceder` | Override the data directory |
| `INTERCEDER_GATEWAY_HOST` | `127.0.0.1` | Gateway bind address |
| `INTERCEDER_GATEWAY_PORT` | `7878` | Gateway bind port |
| `INTERCEDER_SKIP_PREREQ_CHECKS` | unset | Set to `1` to skip install.sh prereq checks |
| `INTERCEDER_SKIP_KEYCHAIN` | unset | Set to `1` to skip Keychain prompts |
| `INTERCEDER_SKIP_LAUNCHD` | unset | Set to `1` to skip launchd install |
| `INTERCEDER_CLONE_DIR` | `~/interceder` | Override bootstrap.sh clone destination |
| `INTERCEDER_SKIP_LAUNCH` | unset | Set to `1` to skip Claude Code launch in bootstrap.sh |

## Post-Install Verification

After installation, verify everything is working:

1. **Services running:** `launchctl list | grep interceder` shows both `com.interceder.gateway` and `com.interceder.manager`
2. **Gateway healthy:** `curl -s http://127.0.0.1:7878/health` returns `{"status":"ok","service":"gateway"}`
3. **Database exists:** `ls ~/Library/Application\ Support/Interceder/db/memory.sqlite`
4. **Config exists:** `cat ~/Library/Application\ Support/Interceder/config.toml`
5. **Webapp (if built):** Open http://127.0.0.1:7878 in a browser

## Uninstall

```bash
# Stop services
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl unload ~/Library/LaunchAgents/com.interceder.manager.plist

# Remove launchd plists
rm ~/Library/LaunchAgents/com.interceder.gateway.plist
rm ~/Library/LaunchAgents/com.interceder.manager.plist

# Remove data directory
rm -rf ~/Library/Application\ Support/Interceder

# Remove repo (optional)
rm -rf ~/interceder
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/install-guide.md
git commit -m "docs: add detailed install guide"
```

---

### Task 5: docs/architecture.md

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Write the doc**

Create `docs/architecture.md`:

```markdown
# Architecture

## Overview

Interceder is a two-process system that provides a persistent Claude Code session accessible from Slack and a web app. Both processes run as macOS launchd daemons on the same machine.

## Processes

### Gateway (`interceder gateway`)

The Gateway is a FastAPI/uvicorn server that handles all external communication:

- **REST API** on `127.0.0.1:7878` — health checks, dashboard endpoints
- **WebSocket** at `/ws` — real-time communication with the webapp
- **Slack Socket Mode** — receives Slack DMs via a background thread
- **Outbox drain** — polls the outbox table every 0.5s and delivers messages to Slack and webapp clients

**Key files:**
- `src/interceder/gateway/service.py` — entry point, starts uvicorn + Slack thread
- `src/interceder/gateway/app.py` — FastAPI app factory, health endpoint, lifespan
- `src/interceder/gateway/api.py` — REST API routes (`/api/workers`, `/api/approvals`, `/api/memory/search`, `/api/loops`, etc.)
- `src/interceder/gateway/ws.py` — WebSocket handler, client tracking, broadcast
- `src/interceder/gateway/slack_handler.py` — normalizes Slack events into canonical Messages
- `src/interceder/gateway/queue.py` — inbox/outbox SQLite queue helpers
- `src/interceder/gateway/outbox_drain.py` — drains outbox → Slack + webapp

### Manager Supervisor (`interceder manager`)

The Manager is the AI brain — a long-lived Claude Opus session:

- Drains the inbox table for new messages
- Passes messages through a Claude Agent SDK session
- Writes responses to the outbox table
- Manages persistent memory (SQLite archive + structured extraction)
- Spawns ephemeral Worker subagents for concrete tasks
- Handles approval gates, scheduled tasks, and proactive messages

**Key files:**
- `src/interceder/manager/service.py` — entry point
- `src/interceder/manager/supervisor.py` — main loop (`tick()`)
- `src/interceder/manager/session.py` — Agent SDK session wrapper
- `src/interceder/manager/inbox_drain.py` — processes inbox messages
- `src/interceder/manager/prompt.py` — system prompt assembly
- `src/interceder/manager/tools.py` — tool registry for the Manager
- `src/interceder/manager/worker_mgr.py` — spawns and manages Workers
- `src/interceder/manager/proactive.py` — proactive message delivery

## Message Flow

```
User (Slack DM or webapp)
    │
    ▼
Gateway
    ├─ Slack Socket Mode handler → normalize_slack_event()
    │   or
    ├─ WebSocket handler → ws_endpoint()
    │
    ▼
enqueue_inbox(conn, message)  →  inbox table (SQLite)
    │
    ▼
Manager Supervisor
    ├─ inbox_drain.py reads queued messages
    ├─ passes to Claude Agent SDK session
    ├─ session produces response + tool calls
    │
    ▼
enqueue_outbox(conn, response)  →  outbox table (SQLite)
    │
    ▼
Gateway (outbox drain loop, every 0.5s)
    ├─ Slack: send via slack_sdk WebClient
    └─ Webapp: broadcast via WebSocket
```

## Database

SQLite with WAL (Write-Ahead Logging) mode. Single database file at `~/Library/Application Support/Interceder/db/memory.sqlite`.

### Schema (6 migrations)

| Migration | Tables | Purpose |
|-----------|--------|---------|
| `0001_init.sql` | `inbox`, `outbox` | Durable message queues between Gateway and Manager |
| `0002_memory_archive.sql` | `messages`, `messages_fts5`, `entities`, `facts`, `reflections` | Full message archive with FTS5 full-text search |
| `0003_workers.sql` | `workers`, `worker_events`, `worker_transcripts` | Worker subprocess tracking |
| `0004_approvals.sql` | `approvals`, `approval_resolutions` | Approval queue for Tier 1 actions |
| `0005_loops.sql` | `karpathy_loops`, `loop_iterations`, `loop_metrics` | Self-improvement loop tracking |
| `0006_scheduler.sql` | `scheduled_tasks`, `task_runs` | Cron-like scheduled task execution |

### Key design choices
- **WAL mode** — allows concurrent reads while writing; safe for two-process access
- **Foreign keys enabled** — referential integrity across all tables
- **Synchronous = NORMAL** — WAL-safe balance of durability and performance
- **Idempotent migrations** — safe to re-run

## Workers

Workers are ephemeral Claude Code subprocesses spawned by the Manager:

- Each Worker gets a sandboxed workspace under `~/interceder-workspace/workers/`
- Workers run as separate processes (via Claude Agent SDK or CLI)
- They stream JSONL events back to the Manager
- Workers can be foregrounded (direct user access) or backgrounded
- Worker transcripts are stored in the `worker_transcripts` table

**Key files:**
- `src/interceder/worker/runner.py` — subprocess launcher
- `src/interceder/worker/protocol.py` — event streaming protocol
- `src/interceder/worker/sandbox.py` — sandbox configuration

## Permission Tiers

| Tier | Policy | Examples |
|------|--------|---------|
| 0 — Autonomous | No approval needed | File reads, tests, local builds, memory writes, spawning workers |
| 1 — Approval-gated | User must approve via Slack reaction or webapp button | `git push`, merge PRs, install global packages, external API calls |
| 2 — Hard-blocked | Never allowed regardless of mode | Destructive `rm`, force-push to protected branches, credential store writes, system modifications |

**Key files:**
- `src/interceder/approval/tiers.py` — tier classification logic
- `src/interceder/approval/checker.py` — approval checking
- `src/interceder/approval/afk.py` — AFK autopilot mode with scoped grants

## Memory Architecture

### Hot Memory (always in prompt)
Small, curated context: Manager identity, active task, pinned user facts, recent turns. Budget: single-digit thousands of tokens.

### Cold Memory (session archive)
SQLite + FTS5 full-text search. Stores everything: messages, tool calls, worker transcripts, decisions. Append-only.

### Structured Layer
LLM-driven extraction of facts, entities, relationships, and reflections from raw archive data. Enables "remember when we..." queries.

## Self-Improvement Loops (Karpathy System)

Three layered scopes:
- **L1 — User Model** — learns how the user phrases requests, preferences, shorthand
- **L2 — Skills Library** — after tasks, reflects and writes/edits persistent skills
- **L3 — Project Layer** — runs time-boxed experiments against scalar metrics

**Key files:**
- `src/interceder/loops/core.py` — core loop logic
- `src/interceder/loops/l1_user_model.py`, `l2_skills.py`, `l3_project.py` — layer implementations
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture overview"
```

---

### Task 6: docs/configuration.md

**Files:**
- Create: `docs/configuration.md`

- [ ] **Step 1: Write the doc**

Create `docs/configuration.md`:

```markdown
# Configuration

## config.toml

Location: `~/Library/Application Support/Interceder/config.toml`

Generated during installation. All values are non-secret — secrets use macOS Keychain references.

### [general]

| Key | Default | Description |
|-----|---------|-------------|
| `user_id` | `"me"` | Your identity. Used as default on all memory entries. Populated from Slack user ID or webapp session when available. |

### [allowlist]

| Key | Default | Description |
|-----|---------|-------------|
| `paths` | `[]` | List of repo root paths the Manager and Workers are allowed to write to. E.g. `["~/code/myrepo", "~/projects/other"]` |

### [quiet_hours]

| Key | Default | Description |
|-----|---------|-------------|
| `start` | `"23:00"` | When quiet hours begin (proactive messages suppressed) |
| `end` | `"07:00"` | When quiet hours end |
| `timezone` | `"local"` | Timezone for quiet hours |

### [proactive.rate_limit_seconds]

Controls how frequently proactive messages can be sent, by type:

| Key | Default | Description |
|-----|---------|-------------|
| `worker_done` | `30` | Minimum seconds between "worker finished" notifications |
| `approval` | `0` | Minimum seconds between approval requests (0 = no limit) |
| `failure` | `0` | Minimum seconds between failure notifications |
| `idle_reflection` | `900` | Minimum seconds between idle reflection messages (15 min) |
| `opportunistic` | `3600` | Minimum seconds between opportunistic suggestions (1 hr) |

### [secrets]

These are **Keychain entry names**, not secret values. Each points to a macOS Keychain entry under the service name `"interceder"`:

| Key | Keychain Entry | Purpose |
|-----|---------------|---------|
| `slack_bot_token` | `interceder/slack_bot_token` | Slack Bot User OAuth Token (`xoxb-...`) |
| `slack_app_token` | `interceder/slack_app_token` | Slack App-Level Token (`xapp-...`) for Socket Mode |
| `webapp_jwt_key` | `interceder/webapp_jwt_key` | JWT signing key for webapp authentication |
| `veo_api_key` | `interceder/veo_api_key` | Google Veo API key for video generation |
| `gemini_api_key` | `interceder/gemini_api_key` | Google Gemini API key for image generation |

### Setting Keychain secrets

```bash
# Store a secret
security add-generic-password -a "interceder" -s "interceder/slack_bot_token" -w "xoxb-your-token-here"

# Retrieve a secret (verify)
security find-generic-password -a "interceder" -s "interceder/slack_bot_token" -w

# Delete a secret
security delete-generic-password -a "interceder" -s "interceder/slack_bot_token"
```

In Python, secrets are accessed via the `keyring` library:
```python
import keyring
token = keyring.get_password("interceder", "slack_bot_token")
```

## Environment Variable Overrides

| Variable | Overrides | Default |
|----------|-----------|---------|
| `INTERCEDER_HOME` | Data directory path | `~/Library/Application Support/Interceder` |
| `INTERCEDER_GATEWAY_HOST` | Gateway bind address | `127.0.0.1` |
| `INTERCEDER_GATEWAY_PORT` | Gateway bind port | `7878` |
| `INTERCEDER_SLACK_APP_TOKEN` | Keychain lookup for Slack app token | (uses Keychain) |
| `INTERCEDER_SLACK_BOT_TOKEN` | Keychain lookup for Slack bot token | (uses Keychain) |

## Model Configuration

Model IDs are defined in `src/interceder/config.py`:

| Constant | Value | Used For |
|----------|-------|----------|
| `MANAGER_MODEL` | `claude-opus-4-6` | Manager Supervisor session |
| `WORKER_DEFAULT_MODEL` | `claude-sonnet-4-6` | Worker subagent sessions |
| `CLASSIFIER_MODEL` | `claude-haiku-4-5-20251001` | Tier classification, routing |

To change models, edit `src/interceder/config.py` and restart services.
```

- [ ] **Step 2: Commit**

```bash
git add docs/configuration.md
git commit -m "docs: add configuration reference"
```

---

### Task 7: docs/slack-setup.md

**Files:**
- Create: `docs/slack-setup.md`

- [ ] **Step 1: Write the doc**

Create `docs/slack-setup.md`:

```markdown
# Slack Setup

Slack integration is optional and can be configured after installation. It lets you message Interceder from any device via Slack DMs.

## Overview

Interceder uses **Slack Socket Mode** — no public URL or ngrok required. The Gateway maintains a persistent WebSocket connection to Slack's servers.

## Step 1: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Name it `Interceder` (or whatever you prefer)
4. Select your workspace
5. Click **Create App**

## Step 2: Enable Socket Mode

1. In the app settings, go to **Socket Mode** (left sidebar)
2. Toggle **Enable Socket Mode** to ON
3. You'll be prompted to create an **App-Level Token**:
   - Name: `interceder-socket`
   - Scope: `connections:write`
   - Click **Generate**
4. **Copy the token** (starts with `xapp-`) — you'll need it in Step 5

## Step 3: Configure Bot Permissions

1. Go to **OAuth & Permissions** (left sidebar)
2. Under **Bot Token Scopes**, add:
   - `chat:write` — send messages
   - `im:history` — read DM history
   - `im:read` — access DM channel info
   - `im:write` — open/manage DMs
   - `files:read` — access file attachments

## Step 4: Subscribe to Events

1. Go to **Event Subscriptions** (left sidebar)
2. Toggle **Enable Events** to ON
3. Under **Subscribe to bot events**, add:
   - `message.im` — receive DM messages
4. Click **Save Changes**

## Step 5: Install the App to Your Workspace

1. Go to **Install App** (left sidebar)
2. Click **Install to Workspace**
3. Review permissions and click **Allow**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`)

## Step 6: Store Tokens in Keychain

```bash
# Store the Bot token
security add-generic-password -a "interceder" -s "interceder/slack_bot_token" -w "xoxb-your-bot-token"

# Store the App-Level token
security add-generic-password -a "interceder" -s "interceder/slack_app_token" -w "xapp-your-app-token"
```

## Step 7: Restart the Gateway

```bash
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
```

## Step 8: Test

1. Open Slack and find the `Interceder` bot in your DMs
2. Send a message — it should be enqueued in the inbox
3. Check the Gateway logs for confirmation:

```bash
tail -f ~/Library/Application\ Support/Interceder/logs/gateway.log
```

You should see: `enqueued inbox: slack-...`

## Troubleshooting

**"Slack tokens not found — running without Slack"**
The Gateway starts without Slack if tokens aren't configured. Check:
```bash
security find-generic-password -a "interceder" -s "interceder/slack_bot_token" -w
security find-generic-password -a "interceder" -s "interceder/slack_app_token" -w
```

**Messages not arriving**
- Verify the bot is in your DMs (not a channel)
- Check that `message.im` event subscription is enabled
- Check Socket Mode is enabled
- Look at `gateway.err.log` for connection errors

**"Slack Socket Mode crashed"**
Usually a token issue. Regenerate tokens and re-store in Keychain.
```

- [ ] **Step 2: Commit**

```bash
git add docs/slack-setup.md
git commit -m "docs: add Slack setup guide"
```

---

### Task 8: docs/webapp.md

**Files:**
- Create: `docs/webapp.md`

- [ ] **Step 1: Write the doc**

Create `docs/webapp.md`:

```markdown
# Web App

Interceder includes a React/TypeScript web dashboard for chatting with the Manager, viewing workers, managing approvals, and searching memory.

## Building

Requires Node.js 18+ and npm.

```bash
cd webapp
npm install
npm run build
```

Built assets go to `webapp/dist/`. The Gateway serves them at `http://127.0.0.1:7878`.

### Development mode

```bash
cd webapp
npm run dev
```

Starts Vite dev server on `http://localhost:5173` with hot reload. API requests proxy to the Gateway on port 7878.

## Tech Stack

- **React 19** + **TypeScript 5.6**
- **Vite 6** — build tool and dev server
- **WebSocket** — real-time communication with the Gateway

## Components

| Component | File | Purpose |
|-----------|------|---------|
| Layout | `src/components/Layout.tsx` | Main layout, tab navigation |
| ChatPane | `src/components/ChatPane.tsx` | Chat interface — send messages, see responses |
| MessageBubble | `src/components/MessageBubble.tsx` | Individual message display |
| WorkersPane | `src/components/WorkersPane.tsx` | Active/completed workers list |
| ApprovalsPane | `src/components/ApprovalsPane.tsx` | Pending approval requests |
| MemoryPane | `src/components/MemoryPane.tsx` | Full-text memory search |
| SettingsPane | `src/components/SettingsPane.tsx` | Configuration and status |

## WebSocket API

The webapp connects to `ws://127.0.0.1:7878/ws` (or via Tailscale IP).

### Client → Server messages

**Send a message:**
```json
{
  "type": "message",
  "content": "Hello, Interceder",
  "correlation_id": "webapp:abc123"
}
```

**Ping (keep-alive):**
```json
{ "type": "ping" }
```

### Server → Client messages

**Acknowledgment:**
```json
{
  "type": "ack",
  "message_id": "webapp-abc123def456"
}
```

**Pong:**
```json
{ "type": "pong" }
```

**Manager response (broadcast from outbox drain):**
```json
{
  "type": "message",
  "id": "outbox-id",
  "content": "Here's what I found...",
  "source": "manager",
  "kind": "text",
  "created_at": 1712700000
}
```

## REST API Endpoints

The Gateway exposes these dashboard endpoints at `/api/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Gateway health check |
| `/api/workers` | GET | List workers (optional `?status=running`) |
| `/api/approvals` | GET | List approvals (default `?status=pending`) |
| `/api/memory/search` | GET | Full-text search (`?q=search+term`) |
| `/api/loops` | GET | List Karpathy loops |
| `/api/audit` | GET | Audit log (optional `?limit=100`) |
| `/api/afk/grants` | GET | Active AFK grants |
| `/api/schedules` | GET | Scheduled tasks |

## Remote Access via Tailscale

If Tailscale is configured, the webapp is accessible from any device on your Tailscale network:

```
http://<tailscale-ip>:7878
```

The Gateway binds to `127.0.0.1` by default. To bind to all interfaces (required for Tailscale access), set:

```bash
export INTERCEDER_GATEWAY_HOST=0.0.0.0
```

Then restart the Gateway service.
```

- [ ] **Step 2: Commit**

```bash
git add docs/webapp.md
git commit -m "docs: add webapp build and usage guide"
```

---

### Task 9: docs/troubleshooting.md

**Files:**
- Create: `docs/troubleshooting.md`

- [ ] **Step 1: Write the doc**

Create `docs/troubleshooting.md`:

```markdown
# Troubleshooting

## Log Locations

All logs are in `~/Library/Application Support/Interceder/logs/`:

| File | Contents |
|------|----------|
| `gateway.log` | Gateway stdout — request logs, Slack events, outbox delivery |
| `gateway.err.log` | Gateway stderr — errors, stack traces |
| `manager.log` | Manager stdout — inbox processing, session activity |
| `manager.err.log` | Manager stderr — errors, stack traces |

View logs in real-time:
```bash
tail -f ~/Library/Application\ Support/Interceder/logs/gateway.log
tail -f ~/Library/Application\ Support/Interceder/logs/manager.log
```

## Common Issues

### Gateway won't start

**Symptom:** `launchctl list | grep gateway` shows nothing or a non-zero exit status.

**Check port conflict:**
```bash
lsof -i :7878
```
If another process is using port 7878, either stop it or change the port:
```bash
# In the gateway plist, or via env var:
export INTERCEDER_GATEWAY_PORT=7879
```

**Check logs:**
```bash
cat ~/Library/Application\ Support/Interceder/logs/gateway.err.log
```

**Common causes:**
- Port 7878 already in use
- Python dependencies not installed (`uv sync` needed)
- Database file doesn't exist (run `uv run python -m interceder migrate`)

### Manager won't start

**Check logs:**
```bash
cat ~/Library/Application\ Support/Interceder/logs/manager.err.log
```

**Common causes:**
- Database not initialized — run `uv run python -m interceder migrate`
- Claude CLI not installed (Manager needs it for Agent SDK sessions)
- Missing `ANTHROPIC_API_KEY` environment variable

### Services not running after reboot

launchd should restart services automatically (`RunAtLoad` + `KeepAlive` are set in the plists). If they're not running:

```bash
# Check if plists are installed
ls ~/Library/LaunchAgents/com.interceder.*.plist

# Reload them
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.manager.plist
```

### Slack messages not arriving

See [Slack Setup — Troubleshooting](slack-setup.md#troubleshooting).

### Database errors

**"no such table" errors:**
```bash
# Re-run migrations
uv run python -m interceder migrate
```

**Check migration state:**
```bash
sqlite3 ~/Library/Application\ Support/Interceder/db/memory.sqlite "SELECT * FROM schema_meta ORDER BY version"
```
Should show versions 1-6.

**WAL mode verification:**
```bash
sqlite3 ~/Library/Application\ Support/Interceder/db/memory.sqlite "PRAGMA journal_mode"
```
Should return `wal`.

**Database locked:**
Usually means a process crashed without releasing the lock. Restart services:
```bash
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl unload ~/Library/LaunchAgents/com.interceder.manager.plist
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.manager.plist
```

### Webapp not loading

**If webapp was built:** Check that `webapp/dist/` exists and contains `index.html`.

**If webapp wasn't built:** `cd webapp && npm install && npm run build`

**If API calls fail:** Check the Gateway is running and healthy:
```bash
curl -s http://127.0.0.1:7878/health
```

## Restarting Services

```bash
# Restart Gateway
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist

# Restart Manager
launchctl unload ~/Library/LaunchAgents/com.interceder.manager.plist
launchctl load ~/Library/LaunchAgents/com.interceder.manager.plist

# Restart both
for svc in gateway manager; do
    launchctl unload ~/Library/LaunchAgents/com.interceder.${svc}.plist
    launchctl load ~/Library/LaunchAgents/com.interceder.${svc}.plist
done
```

## Reset to Clean State

**Warning:** This deletes all data including memory, message history, and configuration.

```bash
# Stop services
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl unload ~/Library/LaunchAgents/com.interceder.manager.plist

# Delete data directory
rm -rf ~/Library/Application\ Support/Interceder

# Re-run install
bash deploy/install.sh
# or launch Claude Code and let it guide you
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/troubleshooting.md
git commit -m "docs: add troubleshooting guide"
```

---

### Task 10: docs/faq.md

**Files:**
- Create: `docs/faq.md`

- [ ] **Step 1: Write the doc**

Create `docs/faq.md`:

```markdown
# FAQ

## What is Interceder?

Interceder is a harness around an always-on Claude Code session running on a Mac. It provides persistent memory, Slack integration, a web dashboard, and the ability to spawn worker subagents for tasks — all accessible remotely from any device. Think of it as a home automation system for your AI assistant.

## What AI models does it use?

| Role | Model | Why |
|------|-------|-----|
| Manager (main brain) | Claude Opus 4.6 | Best reasoning, long-context, manages everything |
| Workers (task execution) | Claude Sonnet 4.6 | Fast, capable, cost-effective for concrete tasks |
| Classification (routing) | Claude Haiku 4.5 | Fast and cheap for tier classification, routing |

Models are configured in `src/interceder/config.py`. See [Configuration](configuration.md#model-configuration).

## Can I run this on Linux?

No. Interceder is macOS-only. It depends on:
- **launchd** for service management (no systemd equivalent is implemented)
- **macOS Keychain** for secret storage (via the `keyring` library)

## Is my data sent to the cloud?

Message content is sent to Anthropic's API for processing (that's how Claude works). Everything else — your database, memory archive, config, worker transcripts — stays on your local machine. No data is sent to any third party besides Anthropic.

## How do I update Interceder?

```bash
cd ~/interceder
git pull
uv sync
uv run python -m interceder migrate
```

Then restart services:
```bash
for svc in gateway manager; do
    launchctl unload ~/Library/LaunchAgents/com.interceder.${svc}.plist
    launchctl load ~/Library/LaunchAgents/com.interceder.${svc}.plist
done
```

## How do I add a repo to the allowlist?

Edit `~/Library/Application Support/Interceder/config.toml`:

```toml
[allowlist]
paths = ["~/code/my-repo", "~/projects/another-repo"]
```

No restart needed — the Manager reads config.toml dynamically.

## How do I stop everything?

```bash
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl unload ~/Library/LaunchAgents/com.interceder.manager.plist
```

To start again:
```bash
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.manager.plist
```

## How do I check if services are running?

```bash
launchctl list | grep interceder
```

Both `com.interceder.gateway` and `com.interceder.manager` should appear with exit status 0.

## What port does the Gateway use?

Default: `127.0.0.1:7878`. Override with environment variables:
```bash
export INTERCEDER_GATEWAY_HOST=0.0.0.0  # bind to all interfaces
export INTERCEDER_GATEWAY_PORT=8080      # use port 8080
```

See [Configuration](configuration.md#environment-variable-overrides).

## Can I use this from my phone?

Yes, if Tailscale is configured. The webapp at `http://<tailscale-ip>:7878` works in mobile browsers. You can also message the Interceder Slack bot from the Slack mobile app.

## What happens if the Mac restarts?

launchd automatically restarts both services on boot (configured via `RunAtLoad` and `KeepAlive` in the plist files). The Manager resumes from its last state using the persistent SQLite database.

## How much does it cost to run?

Interceder itself is free. You pay for Claude API usage through your Anthropic account. Costs depend on how much you use it — the Manager uses Opus (most expensive) and Workers use Sonnet (cheaper). The cost tracker tool in `src/interceder/tools/cost_tracker.py` helps monitor spend.
```

- [ ] **Step 2: Commit**

```bash
git add docs/faq.md
git commit -m "docs: add FAQ"
```

---

### Task 11: docs/launchd.md

**Files:**
- Create: `docs/launchd.md`

- [ ] **Step 1: Write the doc**

Create `docs/launchd.md`:

```markdown
# Launchd Services

Interceder runs as two macOS launchd user agents (daemons). They start automatically on login and restart if they crash.

## Services

| Service | Label | Plist | What it runs |
|---------|-------|-------|-------------|
| Gateway | `com.interceder.gateway` | `~/Library/LaunchAgents/com.interceder.gateway.plist` | `uv run python -m interceder gateway` |
| Manager | `com.interceder.manager` | `~/Library/LaunchAgents/com.interceder.manager.plist` | `uv run python -m interceder manager` |

## Plist Templates

The source templates are in `deploy/`:
- `deploy/com.interceder.gateway.plist`
- `deploy/com.interceder.manager.plist`

During installation, these placeholders are replaced:

| Placeholder | Replaced with |
|-------------|--------------|
| `__INTERCEDER_HOME__` | `~/Library/Application Support/Interceder` |
| `__INTERCEDER_REPO__` | Absolute path to the cloned repo (e.g. `~/interceder`) |
| `__INTERCEDER_UV_BIN__` | Absolute path to the `uv` binary (e.g. `/usr/local/bin/uv`) |

## Plist Configuration

Both plists share these settings:

| Key | Value | Meaning |
|-----|-------|---------|
| `RunAtLoad` | `true` | Start when the plist is loaded (including at login) |
| `KeepAlive` | `true` | Restart automatically if the process exits |
| `ProcessType` | `Interactive` | Higher scheduling priority |

### Gateway-specific environment

| Variable | Value |
|----------|-------|
| `INTERCEDER_HOME` | Data directory path |
| `INTERCEDER_GATEWAY_HOST` | `127.0.0.1` |
| `INTERCEDER_GATEWAY_PORT` | `7878` |

### Manager-specific environment

| Variable | Value |
|----------|-------|
| `INTERCEDER_HOME` | Data directory path |

### Log paths

| Service | stdout | stderr |
|---------|--------|--------|
| Gateway | `<INTERCEDER_HOME>/logs/gateway.log` | `<INTERCEDER_HOME>/logs/gateway.err.log` |
| Manager | `<INTERCEDER_HOME>/logs/manager.log` | `<INTERCEDER_HOME>/logs/manager.err.log` |

## Managing Services

### Start

```bash
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.manager.plist
```

### Stop

```bash
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl unload ~/Library/LaunchAgents/com.interceder.manager.plist
```

### Restart

```bash
for svc in gateway manager; do
    launchctl unload ~/Library/LaunchAgents/com.interceder.${svc}.plist
    launchctl load ~/Library/LaunchAgents/com.interceder.${svc}.plist
done
```

### Check status

```bash
launchctl list | grep interceder
```

Output shows: PID, exit status, label. A PID means it's running. Exit status 0 means it exited cleanly.

### View recent logs

```bash
# Gateway
tail -50 ~/Library/Application\ Support/Interceder/logs/gateway.log
tail -50 ~/Library/Application\ Support/Interceder/logs/gateway.err.log

# Manager
tail -50 ~/Library/Application\ Support/Interceder/logs/manager.log
tail -50 ~/Library/Application\ Support/Interceder/logs/manager.err.log
```

## Troubleshooting

### Service keeps restarting (crash loop)

Check the error log for the crashing service:
```bash
cat ~/Library/Application\ Support/Interceder/logs/gateway.err.log
```

Common causes:
- Missing Python dependencies → `cd ~/interceder && uv sync`
- Database not initialized → `uv run python -m interceder migrate`
- Port conflict (Gateway) → `lsof -i :7878`

### Service won't load

```bash
# Check for syntax errors in the plist
plutil ~/Library/LaunchAgents/com.interceder.gateway.plist
```

If the plist has placeholder values (`__INTERCEDER_*__`), the installation didn't complete. Re-run:
```bash
bash deploy/install.sh
```

### Plist changes not taking effect

After editing a plist:
```bash
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
```

`launchctl` caches the plist on load — you must unload/reload for changes to take effect.
```

- [ ] **Step 2: Commit**

```bash
git add docs/launchd.md
git commit -m "docs: add launchd services guide"
```

---

### Task 12: Final Verification

- [ ] **Step 1: Run the bootstrap script tests**

```bash
cd /Users/marcsinger/Downloads/interceder && uv run pytest tests/test_bootstrap_script.py -v
```

Expected: All tests PASS.

- [ ] **Step 2: Run the full test suite**

```bash
cd /Users/marcsinger/Downloads/interceder && uv run pytest -v
```

Expected: All existing tests still pass (no regressions).

- [ ] **Step 3: Verify all files exist**

```bash
ls -la deploy/bootstrap.sh CLAUDE.md README.md
ls docs/install-guide.md docs/architecture.md docs/configuration.md docs/slack-setup.md docs/webapp.md docs/troubleshooting.md docs/faq.md docs/launchd.md
```

Expected: All 11 files present.

- [ ] **Step 4: Verify bootstrap.sh is executable**

```bash
test -x deploy/bootstrap.sh && echo "OK" || echo "NOT EXECUTABLE"
```

Expected: `OK`

- [ ] **Step 5: Final commit (if any unstaged changes)**

```bash
git status
# If there are changes:
git add -A
git commit -m "chore: final verification pass"
```
