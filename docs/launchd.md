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
