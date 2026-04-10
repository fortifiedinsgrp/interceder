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
            launchctl unload "${plist}" || true
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
    health="$(curl -sf http://127.0.0.1:7878/health)" || die "gateway did not respond to health check"
    if [[ "${health}" != *'"status":"ok"'* ]]; then
        die "gateway health check failed: ${health}"
    fi

    if grep -q "echo stub" "${INTERCEDER_HOME}/logs/manager.err.log" 2>/dev/null; then
        die "manager is still in echo stub mode after update — check ${INTERCEDER_HOME}/logs/manager.err.log"
    fi

    log "all checks passed"
fi

log "update complete"
