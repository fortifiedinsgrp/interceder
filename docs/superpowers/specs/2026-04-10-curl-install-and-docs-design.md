# Curl Install + AI-Guided Setup + Documentation

**Status:** Design approved
**Date:** 2026-04-10

## Goal

Make Interceder installable via a single `curl` command from GitHub. After bootstrap, Claude Code takes over — reading extensive in-repo documentation to walk the user through installation interactively, answer questions, and troubleshoot issues.

## Target Audience

The primary user (Marc) and technical teammates at Fortified who are comfortable with the terminal but may not know Interceder's internals.

## Design

### 1. Bootstrap Script — `deploy/bootstrap.sh`

A thin (~50-line) bash script, curl-able from GitHub:

```
curl -fsSL https://raw.githubusercontent.com/fortifiedinsgrp/interceder/main/deploy/bootstrap.sh | bash
```

The script does exactly three things:

1. **Check bare minimum prereqs** — `git` and `claude` CLI exist. If either is missing, print a clear error with install instructions and exit.
2. **Clone the repo** — clone `fortifiedinsgrp/interceder` to `~/interceder`. If the directory already exists, `git pull` to update instead.
3. **Launch Claude Code** — `cd ~/interceder && claude`. Claude Code starts, reads `CLAUDE.md`, detects that Interceder is not yet installed, and offers to guide the user through setup.

Environment variables:
- `INTERCEDER_CLONE_DIR` — override the clone destination (default: `~/interceder`)

The script must NOT:
- Install Python, uv, Tailscale, or any other dependency
- Run the install script directly
- Modify system configuration
- Require `sudo`

### 2. CLAUDE.md — Install Runbook

`CLAUDE.md` lives in the repo root. It serves two purposes:
1. General project guidance for Claude Code sessions in this repo
2. An install runbook that Claude Code follows when it detects a fresh machine

#### Structure

```markdown
# Interceder

## Project Overview
Brief description — what Interceder is, two-process architecture, macOS-only.

## Installation

### Detecting Install State
- If `~/Library/Application Support/Interceder/` does not exist → offer to install
- If it exists but services aren't running → offer to repair/restart
- If everything is running → skip, operate normally

### Install Runbook
When the user accepts the install offer, follow these steps in order:

1. **Check prerequisites**
   - macOS (fail if not)
   - Python 3.12 or 3.13 (`python3 --version`)
   - uv (`uv --version`) — if missing, offer: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Tailscale (`tailscale --version`) — warn if missing, not required for local-only use
   - Explain what each prereq is for if the user asks

2. **Install Python dependencies**
   - `cd <repo_root> && uv sync`

3. **Create directory structure**
   - `~/Library/Application Support/Interceder/` with subdirs:
     db/, blobs/, claude-config/skills/, claude-config/agents/,
     claude-config/plugins/, workers/, logs/

4. **Generate config.toml**
   - Ask the user for their preferred `user_id` (default: "me")
   - Ask about quiet hours preferences (default: 23:00-07:00)
   - Write to `~/Library/Application Support/Interceder/config.toml`
   - If config.toml already exists, leave it alone

5. **Run database migrations**
   - `uv run python -m interceder migrate`

6. **Seed Claude config**
   - Write `claude-config/settings.json`
   - Initialize skills git repo

7. **Build the webapp**
   - `cd webapp && npm install && npm run build`
   - This step is optional — skip if npm is not installed

8. **Install launchd services**
   - Install and load `com.interceder.gateway.plist` and `com.interceder.manager.plist`
   - Explain what each service does

9. **Verify**
   - Check both services are running: `launchctl list | grep interceder`
   - Hit the Gateway health endpoint: `curl http://127.0.0.1:7878/health`
   - Report success or diagnose failures

### Post-Install
- Tell the user: "Slack integration is optional. Ask me to 'configure Slack' when you're ready."
- Point to `docs/troubleshooting.md` for common issues

## Development
Standard project guidance — how to run tests, code style, etc.
```

#### Key Design Decisions
- The runbook is imperative (tells Claude Code what commands to run) but Claude Code adapts, explains, and recovers from errors naturally
- Each step has enough context that Claude Code can answer "why" questions
- The detection logic runs automatically — Claude Code offers to install without being asked
- Config generation is interactive — Claude Code asks the user for preferences rather than silently writing defaults

### 3. Documentation Directory — `docs/`

Seven operational reference documents. Each is written for AI consumption — clear headings, explicit paths/commands, no ambiguity. Claude Code reads these when answering questions or troubleshooting.

#### `docs/install-guide.md`
- Complete manual install steps (mirrors what Claude Code does, for reference)
- Full prerequisite list with version requirements and install commands
- All environment variable overrides (`INTERCEDER_HOME`, `INTERCEDER_SKIP_*`, etc.)
- Post-install verification checklist

#### `docs/architecture.md`
- Two-process split: Gateway (FastAPI/Slack Socket Mode) + Manager Supervisor (Claude Agent SDK)
- Message flow diagram: Slack/webapp → Gateway → inbox → Manager → outbox → Gateway → delivery
- SQLite database schema overview (6 migrations, WAL mode)
- Worker subprocess model
- Memory architecture (hot/cold, FTS5, structured extraction)

#### `docs/configuration.md`
- Every `config.toml` option with description and default
- Keychain secret entries (names, what they're for, how to set them)
- Environment variable overrides for all services
- Gateway bind host/port configuration
- Model ID configuration (`config.py`)

#### `docs/slack-setup.md`
- Step-by-step: create Slack app, configure Socket Mode, get bot + app tokens
- Required OAuth scopes
- How to store tokens in macOS Keychain
- Testing the Slack connection
- This is a separate post-install step, not part of initial setup

#### `docs/webapp.md`
- Building the React/Vite webapp (`npm install && npm run build`)
- How the Gateway serves the built assets
- WebSocket API for real-time updates
- Component overview (ChatPane, WorkersPane, ApprovalsPane, MemoryPane, SettingsPane)

#### `docs/troubleshooting.md`
- Common errors and their fixes:
  - "Gateway won't start" → check port 7878, check logs
  - "Manager can't connect to database" → check path, run migrations
  - "Slack messages not arriving" → check tokens, check Socket Mode
  - "Services not running after reboot" → check launchd plists
- Log file locations (`~/Library/Application Support/Interceder/logs/`)
- How to restart services (`launchctl unload/load`)
- How to reset to a clean state
- Database debugging (checking migration state, WAL mode)

#### `docs/faq.md`
- "What is Interceder?" — one-paragraph explanation
- "What model does it use?" — Opus for Manager, Sonnet for Workers, Haiku for classification
- "Can I run this on Linux?" — No, macOS-only (launchd, Keychain)
- "Is my data sent to the cloud?" — Only to Anthropic's API; everything else is local
- "How do I update?" — `git pull && uv sync && uv run python -m interceder migrate`
- "How do I add a new repo to the allowlist?" — edit config.toml
- "How do I stop everything?" — `launchctl unload` both plists

#### `docs/launchd.md`
- How the two daemons work (Gateway, Manager)
- Plist template variables and what they resolve to
- Manual start/stop/restart commands
- Viewing logs via `launchctl` and log files
- Troubleshooting daemon issues (exit codes, restart policies)

### 4. README.md

The GitHub landing page. Written for both humans scanning on GitHub and AI agents consuming it for context.

```markdown
# Interceder

A persistent, conversational AI assistant that runs on a dedicated Mac — accessible remotely from Slack and a web app. Drive your "home" Claude Code from any device, anywhere.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/fortifiedinsgrp/interceder/main/deploy/bootstrap.sh | bash
```

This clones the repo and launches Claude Code, which walks you through the rest.

## Prerequisites

- macOS (required)
- [Claude Code](https://claude.ai/claude-code) CLI
- Python 3.12+ 
- [uv](https://docs.astral.sh/uv/) package manager
- [Tailscale](https://tailscale.com/) (for remote access)

## How It Works

Interceder runs two persistent services on your Mac:

- **Gateway** — FastAPI server + Slack Socket Mode listener. Receives messages from Slack and the webapp, queues them for the Manager.
- **Manager** — A long-lived Claude Opus session that processes messages, manages memory, spawns Workers for tasks, and delivers responses.

Messages flow: Slack/webapp → Gateway → inbox queue → Manager → outbox queue → Gateway → Slack/webapp.

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

After installation, ask Claude Code to "configure Slack" — it will walk you through creating a Slack app and connecting it.

## Manual Install (without Claude Code)

If you prefer to install without AI guidance:

```bash
bash deploy/install.sh
```
```

### 5. Existing `deploy/install.sh`

Kept as-is. No modifications. Serves as a fallback for users who want to install without Claude Code, and as a reference implementation that the CLAUDE.md runbook mirrors.

## What's NOT in Scope

- Slack setup during initial install (separate step)
- Linux/Windows support
- Any changes to the existing Python source code
- Changes to the existing `deploy/install.sh`
- Any new Python dependencies
