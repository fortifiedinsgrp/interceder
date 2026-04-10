#!/usr/bin/env bash
# deploy/bootstrap.sh — curl-able bootstrap for Interceder.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/fortifiedinsgrp/interceder/main/deploy/bootstrap.sh | bash
#
# Env vars:
#   INTERCEDER_CLONE_DIR  — where to clone (default: ~/interceder)
#   INTERCEDER_SKIP_LAUNCH — set to 1 to skip launching Claude Code (for tests)

set -euo pipefail

CLONE_DIR="${INTERCEDER_CLONE_DIR:-${HOME}/interceder}"
REPO_URL="https://github.com/fortifiedinsgrp/interceder.git"

log()  { printf '[interceder] %s\n' "$*"; }
die()  { printf '[interceder] ERROR: %s\n' "$*" >&2; exit 1; }

# ------------------------------------------------------------------
# 1. Check bare minimum prerequisites
# ------------------------------------------------------------------
command -v git >/dev/null 2>&1 || die "git is not installed. Install it from https://git-scm.com/ or via: xcode-select --install"

# ------------------------------------------------------------------
# 2. Clone or update the repo
# ------------------------------------------------------------------
if [[ -d "${CLONE_DIR}/.git" ]]; then
    log "repo already exists at ${CLONE_DIR} — pulling latest"
    git -C "${CLONE_DIR}" pull --ff-only || log "WARNING: pull failed — continuing with existing checkout"
else
    log "cloning interceder to ${CLONE_DIR}"
    git clone "${REPO_URL}" "${CLONE_DIR}"
fi

# ------------------------------------------------------------------
# 3. Launch Claude Code
# ------------------------------------------------------------------
if [[ "${INTERCEDER_SKIP_LAUNCH:-0}" == "1" ]]; then
    log "skipping Claude Code launch (INTERCEDER_SKIP_LAUNCH=1)"
    log "done — repo is at ${CLONE_DIR}"
    exit 0
fi

if ! command -v claude >/dev/null 2>&1; then
    log "Claude Code CLI is not installed. The repo has been cloned to ${CLONE_DIR}. Install Claude Code from https://claude.ai/claude-code, then run: cd ${CLONE_DIR} && claude"
    exit 0
fi

log "launching Claude Code in ${CLONE_DIR}..."
cd "${CLONE_DIR}" && exec claude "I just ran the Interceder bootstrap script. Please check if Interceder is installed and walk me through the setup."
