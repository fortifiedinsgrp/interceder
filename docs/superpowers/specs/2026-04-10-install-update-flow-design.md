# Install & Update Flow Design

**Date:** 2026-04-10
**Status:** Approved

## Problem

The current install flow only handles two states: not installed, and services not running. A third state exists — services running but code is stale or broken (e.g. manager falling back to echo stub, webapp static files out of date). There is also no automated way to push code fixes from the dev machine to the remote Interceder host.

## Solution

Two deliverables:

1. **`deploy/update.sh`** — a standalone script that updates, rebuilds, and restarts everything. Safe to re-run. No Claude Code required.
2. **Enriched CLAUDE.md detection** — adds State 3 so Claude Code can detect and repair a stale/broken install when opened on the remote machine.

---

## A. `deploy/update.sh`

Runs in the repo root. Steps in order:

1. `git pull --ff-only` — pull latest commits from `origin/main`
2. `uv sync` — install/update Python dependencies
3. Rebuild webapp if npm is available: `cd webapp && npm install && npm run build`
4. Restart launchd services:
   - `launchctl unload` then `launchctl load` for `com.interceder.gateway`
   - `launchctl unload` then `launchctl load` for `com.interceder.manager`
5. Wait 2s, then `curl http://127.0.0.1:7878/health` — fail loudly if not `{"status":"ok"}`.

Fails fast (`set -euo pipefail`). Logs each step with `[update]` prefix. Exits 0 on success.

**Env var opt-outs** (matching install.sh pattern):
- `INTERCEDER_SKIP_WEBAPP=1` — skip npm build (useful when Node isn't available)
- `INTERCEDER_SKIP_LAUNCHD=1` — skip service restart (useful in CI)

---

## B. CLAUDE.md: State 3 Detection

Added after the existing State 2 check, before "operate normally":

**Trigger conditions (either):**
- `git -C <repo_root> fetch origin --quiet 2>/dev/null; git -C <repo_root> rev-list HEAD..origin/main --count` returns > 0
- `grep -q "echo stub" ~/Library/Application\ Support/Interceder/logs/manager.err.log 2>/dev/null`

**Offer to user:**
> "Interceder is running but there's an update available (or the manager is in fallback/echo mode). Want me to update and restart?"

**Repair sequence (Claude Code executes interactively):**
1. `git -C <repo_root> pull --ff-only`
2. `uv sync` (from repo root)
3. Rebuild webapp if npm available
4. Restart gateway and manager via launchctl
5. Verify `/health` returns ok
6. Confirm manager log no longer contains "echo stub"

**No change to States 1, 2, or 4.**

---

## Out of Scope

- Automatic background update checking
- Rollback on failed update
- Multi-machine orchestration

---

## Files Changed

| File | Change |
|---|---|
| `deploy/update.sh` | New file |
| `CLAUDE.md` | Add State 3 detection block (≈15 lines) |
