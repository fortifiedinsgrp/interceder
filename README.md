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
      |
  Gateway (enqueue -> inbox table)
      |
  Manager Supervisor (drain inbox -> Claude session -> enqueue outbox)
      |
  Gateway (drain outbox -> Slack / webapp delivery)
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
