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
