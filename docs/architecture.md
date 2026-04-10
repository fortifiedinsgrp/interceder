# Architecture

## Overview

Interceder is a two-process system that provides a persistent Claude Code session accessible from Slack and a web app. Both processes run as macOS launchd daemons on the same machine.

## Processes

### Gateway (`interceder gateway`)

The Gateway is a FastAPI/uvicorn server that handles all external communication:

- **REST API** on `127.0.0.1:7878` — health checks, dashboard endpoints
- **WebSocket** at `/ws` — real-time communication with the webapp
- **Slack Socket Mode** — receives Slack DMs via a background thread
- **Outbox drain** — polls the outbox table every 0.5s and delivers messages to Slack and webapp clients

**Key files:**
- `src/interceder/gateway/service.py` — entry point, starts uvicorn + Slack thread
- `src/interceder/gateway/app.py` — FastAPI app factory, health endpoint, lifespan
- `src/interceder/gateway/api.py` — REST API routes (`/api/workers`, `/api/approvals`, `/api/memory/search`, `/api/loops`, etc.)
- `src/interceder/gateway/ws.py` — WebSocket handler, client tracking, broadcast
- `src/interceder/gateway/slack_handler.py` — normalizes Slack events into canonical Messages
- `src/interceder/gateway/queue.py` — inbox/outbox SQLite queue helpers
- `src/interceder/gateway/outbox_drain.py` — drains outbox → Slack + webapp

### Manager Supervisor (`interceder manager`)

The Manager is the AI brain — a long-lived Claude Opus session:

- Drains the inbox table for new messages
- Passes messages through a Claude Agent SDK session
- Writes responses to the outbox table
- Manages persistent memory (SQLite archive + structured extraction)
- Spawns ephemeral Worker subagents for concrete tasks
- Handles approval gates, scheduled tasks, and proactive messages

**Key files:**
- `src/interceder/manager/service.py` — entry point
- `src/interceder/manager/supervisor.py` — main loop (`tick()`)
- `src/interceder/manager/session.py` — Agent SDK session wrapper
- `src/interceder/manager/inbox_drain.py` — processes inbox messages
- `src/interceder/manager/prompt.py` — system prompt assembly
- `src/interceder/manager/tools.py` — tool registry for the Manager
- `src/interceder/manager/worker_mgr.py` — spawns and manages Workers
- `src/interceder/manager/proactive.py` — proactive message delivery

## Message Flow

```
User (Slack DM or webapp)
    │
    ▼
Gateway
    ├─ Slack Socket Mode handler → normalize_slack_event()
    │   or
    ├─ WebSocket handler → ws_endpoint()
    │
    ▼
enqueue_inbox(conn, message)  →  inbox table (SQLite)
    │
    ▼
Manager Supervisor
    ├─ inbox_drain.py reads queued messages
    ├─ passes to Claude Agent SDK session
    ├─ session produces response + tool calls
    │
    ▼
enqueue_outbox(conn, response)  →  outbox table (SQLite)
    │
    ▼
Gateway (outbox drain loop, every 0.5s)
    ├─ Slack: send via slack_sdk WebClient
    └─ Webapp: broadcast via WebSocket
```

## Database

SQLite with WAL (Write-Ahead Logging) mode. Single database file at `~/Library/Application Support/Interceder/db/memory.sqlite`.

### Schema (6 migrations)

| Migration | Tables | Purpose |
|-----------|--------|---------|
| `0001_init.sql` | `inbox`, `outbox` | Durable message queues between Gateway and Manager |
| `0002_memory_archive.sql` | `messages`, `messages_fts5`, `entities`, `facts`, `reflections` | Full message archive with FTS5 full-text search |
| `0003_workers.sql` | `workers`, `worker_events`, `worker_transcripts` | Worker subprocess tracking |
| `0004_approvals.sql` | `approvals`, `approval_resolutions` | Approval queue for Tier 1 actions |
| `0005_loops.sql` | `karpathy_loops`, `loop_iterations`, `loop_metrics` | Self-improvement loop tracking |
| `0006_scheduler.sql` | `scheduled_tasks`, `task_runs` | Cron-like scheduled task execution |

### Key design choices
- **WAL mode** — allows concurrent reads while writing; safe for two-process access
- **Foreign keys enabled** — referential integrity across all tables
- **Synchronous = NORMAL** — WAL-safe balance of durability and performance
- **Idempotent migrations** — safe to re-run

## Workers

Workers are ephemeral Claude Code subprocesses spawned by the Manager:

- Each Worker gets a sandboxed workspace under `~/interceder-workspace/workers/`
- Workers run as separate processes (via Claude Agent SDK or CLI)
- They stream JSONL events back to the Manager
- Workers can be foregrounded (direct user access) or backgrounded
- Worker transcripts are stored in the `worker_transcripts` table

**Key files:**
- `src/interceder/worker/runner.py` — subprocess launcher
- `src/interceder/worker/protocol.py` — event streaming protocol
- `src/interceder/worker/sandbox.py` — sandbox configuration

## Permission Tiers

| Tier | Policy | Examples |
|------|--------|---------|
| 0 — Autonomous | No approval needed | File reads, tests, local builds, memory writes, spawning workers |
| 1 — Approval-gated | User must approve via Slack reaction or webapp button | `git push`, merge PRs, install global packages, external API calls |
| 2 — Hard-blocked | Never allowed regardless of mode | Destructive `rm`, force-push to protected branches, credential store writes, system modifications |

**Key files:**
- `src/interceder/approval/tiers.py` — tier classification logic
- `src/interceder/approval/checker.py` — approval checking
- `src/interceder/approval/afk.py` — AFK autopilot mode with scoped grants

## Memory Architecture

### Hot Memory (always in prompt)
Small, curated context: Manager identity, active task, pinned user facts, recent turns. Budget: single-digit thousands of tokens.

### Cold Memory (session archive)
SQLite + FTS5 full-text search. Stores everything: messages, tool calls, worker transcripts, decisions. Append-only.

### Structured Layer
LLM-driven extraction of facts, entities, relationships, and reflections from raw archive data. Enables "remember when we..." queries.

## Self-Improvement Loops (Karpathy System)

Three layered scopes:
- **L1 — User Model** — learns how the user phrases requests, preferences, shorthand
- **L2 — Skills Library** — after tasks, reflects and writes/edits persistent skills
- **L3 — Project Layer** — runs time-boxed experiments against scalar metrics

**Key files:**
- `src/interceder/loops/core.py` — core loop logic
- `src/interceder/loops/l1_user_model.py`, `l2_skills.py`, `l3_project.py` — layer implementations
