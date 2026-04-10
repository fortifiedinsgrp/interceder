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
