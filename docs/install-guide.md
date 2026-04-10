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
