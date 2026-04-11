#!/usr/bin/env bash
# deploy/install.sh — first-run setup for Interceder on macOS.
#
# Opt-out env vars (all default to unset/0):
#   INTERCEDER_SKIP_PREREQ_CHECKS  — bypass tool / version checks
#   INTERCEDER_SKIP_KEYCHAIN        — don't prompt for Slack/Veo/Gemini secrets
#   INTERCEDER_SKIP_LAUNCHD         — don't install or load launchd plists
#
# The directory tree under $HOME/Library/Application Support/Interceder is
# always created, config.toml is written if absent, migrations are always
# applied, and claude-config/ is always seeded.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERCEDER_HOME="${HOME}/Library/Application Support/Interceder"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"

log()  { printf '[install] %s\n' "$*"; }
die()  { printf '[install] ERROR: %s\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------------
# 1. Prerequisite checks
# --------------------------------------------------------------------
check_prereqs() {
    if [[ "${INTERCEDER_SKIP_PREREQ_CHECKS:-0}" == "1" ]]; then
        log "skipping prerequisite checks"
        return 0
    fi
    [[ "$(uname -s)" == "Darwin" ]] || die "macOS only"
    command -v python3 >/dev/null || die "python3 not found"
    local py_version
    py_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    case "${py_version}" in
        3.12|3.13) ;;
        *) die "Python 3.12 or 3.13 required (found ${py_version})" ;;
    esac
    command -v git >/dev/null || die "git not found"
    command -v uv  >/dev/null || die "uv not found — install from https://docs.astral.sh/uv/"
    command -v tailscale >/dev/null || log "WARNING: tailscale not found — webapp will be unreachable"
    command -v claude    >/dev/null || log "WARNING: claude CLI not found — Manager will not be able to reason"
}

# --------------------------------------------------------------------
# 2. Directory tree
# --------------------------------------------------------------------
make_dirs() {
    log "creating ${INTERCEDER_HOME}"
    mkdir -p \
        "${INTERCEDER_HOME}/db" \
        "${INTERCEDER_HOME}/blobs" \
        "${INTERCEDER_HOME}/claude-config/skills" \
        "${INTERCEDER_HOME}/claude-config/agents" \
        "${INTERCEDER_HOME}/claude-config/plugins" \
        "${INTERCEDER_HOME}/workers" \
        "${INTERCEDER_HOME}/logs"
}

# --------------------------------------------------------------------
# 3. config.toml
# --------------------------------------------------------------------
write_config_toml() {
    local cfg="${INTERCEDER_HOME}/config.toml"
    if [[ -f "${cfg}" ]]; then
        log "config.toml already exists; leaving it alone"
        return 0
    fi
    log "writing default config.toml"
    cat > "${cfg}" <<'TOML'
# Interceder configuration. Non-secret values only.
# Secrets live in the macOS Keychain under service name "Interceder".

[general]
user_id = "me"

[allowlist]
# Add repo roots here, e.g. paths = ["~/code/repoA", "~/code/repoB"]
paths = []

[quiet_hours]
start = "23:00"
end   = "07:00"
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
TOML
}

# --------------------------------------------------------------------
# 4. memory.sqlite bootstrap via the Python migration runner
# --------------------------------------------------------------------
run_migrations() {
    log "running migrations"
    (
        cd "${REPO_ROOT}"
        INTERCEDER_HOME="${INTERCEDER_HOME}" uv run python -m interceder migrate
    )
}

# --------------------------------------------------------------------
# 5. Claude config scaffolding
# --------------------------------------------------------------------
seed_claude_config() {
    local cc="${INTERCEDER_HOME}/claude-config"
    local settings="${cc}/settings.json"
    if [[ ! -f "${settings}" ]]; then
        log "writing claude-config/settings.json"
        cat > "${settings}" <<'JSON'
{
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "name": "interceder",
    "description": "Interceder harness Claude config — isolated from the user's personal ~/.claude/",
    "permissions": {
        "allow": [],
        "deny": []
    },
    "skills": {
        "directories": ["./skills"]
    }
}
JSON
    fi

    local skills="${cc}/skills"
    if [[ ! -d "${skills}/.git" ]]; then
        log "initializing skills/ git repo"
        (
            cd "${skills}"
            git init -q
            git -c user.email=interceder@localhost -c user.name=Interceder commit \
                --allow-empty -q -m "chore: seed Interceder skill library"
        )
    fi
}

# --------------------------------------------------------------------
# 6. Keychain prompts (stub — real prompts arrive with Phase 1 Slack)
# --------------------------------------------------------------------
prompt_keychain() {
    if [[ "${INTERCEDER_SKIP_KEYCHAIN:-0}" == "1" ]]; then
        log "skipping Keychain prompts"
        return 0
    fi
    log "Keychain setup deferred — run 'interceder setup-secrets' after Phase 1 lands Slack support"
}

# --------------------------------------------------------------------
# 7. launchd plist install
# --------------------------------------------------------------------
install_launchd() {
    if [[ "${INTERCEDER_SKIP_LAUNCHD:-0}" == "1" ]]; then
        log "skipping launchd install"
        return 0
    fi
    mkdir -p "${LAUNCH_AGENTS_DIR}"
    local uv_bin
    uv_bin="$(command -v uv)"
    local interceder_path="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    for name in gateway manager; do
        local src="${REPO_ROOT}/deploy/com.interceder.${name}.plist"
        local dst="${LAUNCH_AGENTS_DIR}/com.interceder.${name}.plist"
        log "installing ${dst}"
        sed \
            -e "s|__INTERCEDER_HOME__|${INTERCEDER_HOME}|g" \
            -e "s|__INTERCEDER_REPO__|${REPO_ROOT}|g" \
            -e "s|__INTERCEDER_UV_BIN__|${uv_bin}|g" \
            -e "s|__INTERCEDER_PATH__|${interceder_path}|g" \
            "${src}" > "${dst}"
        # Unload if already loaded so we pick up changes on reruns.
        launchctl unload "${dst}" >/dev/null 2>&1 || true
        launchctl load "${dst}"
    done
}

main() {
    check_prereqs
    make_dirs
    write_config_toml
    run_migrations
    seed_claude_config
    prompt_keychain
    install_launchd
    log "install complete — INTERCEDER_HOME=${INTERCEDER_HOME}"
}

main "$@"
