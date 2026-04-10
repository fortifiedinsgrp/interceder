# Interceder

Interceder is a remote Claude Code harness — a persistent, conversational AI assistant that runs on a dedicated Mac and is accessible remotely from Slack and a web app. It consists of two services: a Gateway (FastAPI + Slack Socket Mode) and a Manager Supervisor (long-lived Claude Opus session).

## Installation

### Detecting Install State

When starting a session in this repo, check installation state:

1. If `~/Library/Application Support/Interceder/` does not exist → **offer to install**: "Interceder isn't installed yet. Want me to walk you through the setup?"
2. If it exists but services aren't running (`launchctl list | grep interceder` returns nothing) → **offer to repair**: "Interceder is installed but the services aren't running. Want me to start them?"
3. If services are running but either of these is true → **offer to update**: "Interceder is running but there's an update available (or the manager is in fallback/echo mode). Want me to update and restart?"
   - `git fetch origin --quiet 2>/dev/null; git rev-list HEAD..origin/main --count` returns a number > 0 (commits to pull)
   - `grep -q "echo stub" ~/Library/Application\ Support/Interceder/logs/manager.err.log 2>/dev/null` succeeds (manager fell back to echo stub)

   If accepted, run: `bash deploy/update.sh` (from the repo root, which is the current working directory).
   If declined, operate normally.

4. If everything is running and up to date → operate normally.

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
