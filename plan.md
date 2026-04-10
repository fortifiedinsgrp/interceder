# Interceder — Remote Claude Code Harness

**Status:** 🟢 Design complete — ready for implementation planning
**Last updated:** 2026-04-09

## One-line pitch

A harness around an always-on Claude Code session running on a MacBook, accessible remotely from Slack and/or a web app — so you can drive your "home" Claude Code from any device, anywhere.

---

## Decisions

1. **Primary use case:** Option C — a **persistent, conversational Claude Code** that follows the user across devices. Same ongoing session(s) accessible from Slack and a webapp, with full shared history.
2. **Host machine:** a **dedicated Mac** (Mac mini / spare Mac) — not the user's daily-driver. Always-on, sits on the user's home network, runs the harness + Claude Code process(es). macOS-native (launchd, Keychain available). Exact model is a purchasing decision that does not block design.
3. **Memory model — "remembers EVERYTHING":** inspired by the **Hermes agent** (Nous Research) — layered hot/cold memory, long-term structured recall, agent-curated, nothing forgotten unless explicitly pruned. Full schema specified in the **Memory schema** section below.
4. **Self-improvement loop — "Karpathy system":** inspired by Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) loop. Applied in **three layered scopes**, all desired:
   - **L1 — Prompt/user-model layer:** the harness evolves its understanding of *the user* — how they phrase requests, what they mean by shorthand, their preferences — and improves how it rewrites/routes incoming prompts to Claude.
   - **L2 — Skills/playbooks layer (Hermes-style):** after each task, Claude reflects and writes/edits a persistent skill or playbook in a skills library. Next similar task reuses and refines that playbook.
   - **L3 — Project/target layer:** pointed at a specific repo/problem with its own scalar metric (e.g. "make trading bot sharpe go up"), runs Karpathy-style time-boxed experiments on that target.
   - All three are separable modules; we'll build them in order L2 → L1 → L3 (skills layer is the closest to working Hermes pattern, user-model layer builds on its reflection infrastructure, project layer is the most self-contained and can be bolted on).

5. **Session model — Manager + Workers (Hermes-style):**
   - **One long-lived Manager session** is the single conversational surface the user talks to, from any device (Slack, webapp, direct). The Manager is what "remembers everything." Its memory must survive process restarts, crashes, and OS reboots — it is the user's actual assistant.
   - The Manager **spawns ephemeral Worker subagents** (via Claude Code SDK / Task tool) for concrete work: "go implement X in repo Y," "run these experiments," etc. Workers have their own scratchpad, working directory, and can be long-running.
   - Workers **stream status updates** back to the Manager, which decides what to surface to the user and what to record in long-term memory.
   - A Worker can optionally be **"foregrounded"** — promoted to direct conversational access when the user wants fine-grained control (e.g. stepping through a tricky debug). When backgrounded again, its transcript is folded back into the Manager's memory.
   - **Hard constraint:** the Manager must NOT lose memory between sessions/restarts. This drives the memory architecture — Manager state (identity, conversation history, learned user model, skill library, references to active workers) must be fully persisted.

6. **Memory architecture — copy Hermes exactly:**
   - **Hot memory (always in prompt):** small, curated. Manager identity, active task context, pinned user facts, short recent-turns buffer, active skill handles. Hard budget — measured in *single-digit thousands* of tokens, not 200k. The Manager's system prompt is lean on purpose.
   - **Cold memory (session archive):** SQLite + FTS5 full-text search (the Hermes storage pattern). Stores **everything**: all user messages, all Manager replies, all Worker transcripts, all tool calls & outputs, all files read/written (by git ref when possible, snapshot when not), all decisions & rationale, all screenshots/attachments. Append-only by default.
   - **Structured long-term layer (Hindsight-style):** on top of the raw archive, an LLM-driven extraction pass distills facts, entities, relationships, and reflections. This is what supports "remember when we figured out that caching thing?" — the Manager searches the structured layer first, then drills into raw sessions.
   - **Agent-curated promotion/demotion:** the Manager periodically reflects and (a) promotes important new facts into hot memory, (b) demotes stale hot items to cold, (c) writes/refines skills in the skills library. Triggered by task-completion, idle periods, and explicit user nudges.
   - **"Knows to search":** the Manager's system prompt includes an explicit discipline — before answering anything that references prior work, people, preferences, or past decisions, it MUST invoke `session_search` / `memory_recall`. This is enforced by prompt design and a self-check skill, not by code.
   - **Privacy forgetting:** memory is append-only for normal operation, BUT the user can issue `/forget <topic>` or `/redact <range>` commands that tombstone entries. Tombstoned entries are excluded from search and omitted from future context. Full-deletion is an explicit, logged operation.
   - **Pluggable:** memory layer is behind an interface so it can be swapped (e.g. migrate to Hindsight proper, or a vector DB, later).

7. **Authority / permissions model — Tiered + AFK mode:**
   - **Tier 0 — autonomous (no approval):** all reads, scratch work in sandboxed dirs, running tests, local builds, writes to approved working directories, committing to feature branches, writing to the memory archive, spawning workers.
   - **Tier 1 — approval-gated:** `git push`, merging PRs, pushing to shared branches, editing files outside approved repo roots, installing global packages, running DB migrations, any HTTP call that costs money, any message sent to a third party (e.g. Slack DMs to other humans). The Manager queues the action and asks the user for OK via Slack reaction / webapp button.
   - **Tier 2 — never (hard-blocked regardless of mode):** full list specified in the **Security model** section. Summary: destructive `rm` outside sandbox, force-push to protected branches, writes to `~/.ssh/` / Keychain / credential stores, modifications to Interceder's own launchd plists or the Tier-2 list itself, disabling the security hook, sending email/SMS/payments, reading other users' homes, disk/volume modifications.
   - **AFK mode ("I'm out for 4h, autopilot within rails"):** user can issue a scoped autopilot grant — e.g. "approve all Tier-1 actions in repo X for the next 4 hours, budget $Y API spend, nothing destructive." The Manager batches low-risk actions and defers Tier-2 always. Scoped grants are logged and auto-expire.
   - All Tier-1 and Tier-2 decisions are logged to the memory archive (audit trail).

8. **User model — single-user v1, room for a second:**
   - v1 is **strictly single-user (the user).** No auth UI, no multi-tenant memory, no per-user skill libraries.
   - Forward-looking: the only ever possible second user is **the user's wife**. The architecture must leave **one clean seam** for adding a second identity later: a `user_id` column on every memory entry (defaulted to `me` in v1), and a notion of "the Manager knows which human is talking to it." v1 populates this automatically from Slack user ID / webapp session; it's not surfaced in the UI.
   - No other multi-user concerns (tenancy, billing, per-user quotas) — explicitly **out of scope**.

9. **Proactive behavior — the Manager speaks first, across all of these:**
   1. **Worker-done pings** — background task completion + summary + suggested next step.
   2. **Approval requests** — Tier-1 action gates surfaced with ✅ / ❌ reactji (Slack) and buttons (webapp).
   3. **Failure alerts** — crashes, stuck loops, broken tests, budget hits.
   4. **Idle reflection** — during idle periods Manager consolidates hot/cold memory, refines skills, and (when it discovers something user-visible) posts a short "what I learned" note.
   5. **Scheduled tasks** — cron-like: user can say "every weekday at 9am triage GitHub issues on repo X" and the Manager wakes itself to run it.
   6. **Opportunistic suggestions** — pattern-noticing: "you've deployed three times this week, want a one-command deploy skill?" (rate-limited so it doesn't get creepy).
   7. **Memory-triggered reminders** — extracts "remind me about X" intents from past conversations and surfaces them at the right time.
   8. **Morning/evening briefings** — daily digest of overnight Karpathy-loop progress, pending approvals, upcoming schedule items.
   - **Delivery:** all proactive messages go to **both Slack DM and the webapp's inbox** simultaneously; approval actions from either side update the other. Read state syncs between the two.
   - **Quiet hours + digest mode:** user can set quiet hours (e.g. 11pm–7am); during quiet hours, non-urgent pings are batched and delivered at the next digest window. "Urgent" = failure alerts and running-out-of-budget.
   - **Rate limiting:** each class of proactive message has a floor-time between deliveries (esp. opportunistic suggestions) to avoid spam.

10. **Webapp — Chat + Live Dashboard:**
    - **Primary chat pane:** conversational surface with the Manager, at parity with Slack. Threaded worker conversations shown in a sidebar. Same inbox as Slack — read/unread state syncs.
    - **Live workers pane:** list of active Worker subagents with status (running / waiting / done / failed), live-tailing logs, elapsed time, cost-so-far, "foreground this worker" button, "kill" button.
    - **Approvals queue:** all pending Tier-1 actions with one-click ✅ / ❌ and an "explain why" expand.
    - **Karpathy loop dashboard:** for each active L3 loop, a chart of the scalar metric over iterations, current best, recent experiments diff list, pause/resume controls.
    - **Memory browser:** full-text search over the cold archive, filters by date/worker/topic, entity/fact browser from the structured layer, skill library list with read-only skill content preview.
    - **Schedule view:** list of cron-like scheduled tasks with next run times, enable/disable toggles.
    - **Settings:** quiet hours, AFK mode toggle, active approved repo roots, model/budget config.
    - **Diff viewer:** out of scope — we'll link out to GitHub / the local editor instead of building an in-browser diff tool.
    - **Mobile-friendly / responsive:** required. Primary use case is "sit down at any machine (including phone) and drive Claude." The webapp must be first-class on mobile Safari.
    - **Build posture:** start as a chat-only MVP (parity with Slack), add dashboard panes incrementally in a defined order (workers → approvals → memory → Karpathy → schedules → settings).

11. **Filesystem scope & memory location:**
    - **Worker sandbox root:** `~/interceder-workspace/` — default scratch space. Every Worker gets a subdir under here (e.g. `workers/2026-04-09T14-22Z-abc123/`). Used for throwaway experiments, cloning repos to scratch, etc.
    - **Allowlisted repo roots:** a user-managed allowlist of specific paths (e.g. `~/code/repoA`, `~/code/repoB`). Workers can work on these in place. Adding a new path to the allowlist is a Tier-1 action (Manager asks). Allowlist lives in `config.toml`.
    - **Everything else is off-limits.** Including `~/Documents`, `~/Desktop`, `~/Library` (except Interceder's own dir), dotfiles, other users' homes, system paths.
    - **Memory archive location:** `~/Library/Application Support/Interceder/`
      ```
      Interceder/
      ├── db/memory.sqlite       # hot+cold memory, FTS5, schedules, approvals, audit
      ├── blobs/sha256/...       # content-addressed attachments, snapshots, screenshots
      ├── claude-config/         # isolated Claude Code config for the Manager + Workers
      │   ├── settings.json      # Interceder-specific hooks, permissions, MCP servers
      │   ├── skills/            # skill library — its own git repo, Claude Code native skills
      │   ├── agents/            # Interceder-specific subagent definitions
      │   └── plugins/           # MCP servers installed for the harness
      ├── workers/               # per-worker transcripts & state
      ├── config.toml            # non-secret config (allowlist, quiet hours, etc.)
      └── logs/                  # gateway/manager/worker stderr
      ```
    - Rationale: Mac-standard location, Time Machine backs it up, iCloud does NOT sync it (iCloud corrupts SQLite), decoupled from the sandbox (can nuke scratch without losing memory), SQLite-friendly, not accidentally committable to git. Blobs can be symlinked to an external drive if they outgrow the internal disk.
    - **Secrets** (API keys, Slack tokens, webapp JWT secrets) live in the **macOS Keychain**, not in `config.toml`. Accessed via `security` CLI / `keyring` lib.

12. **Models, auth, and cost:**
    - **Claude compute runs on the user's Claude Code Max subscription** — NOT on direct Anthropic API billing. This is a foundational constraint with several architectural consequences:
      - Workers are spawned as **Claude Code CLI / Claude Agent SDK** processes, authenticated via the same login the user already has on the Mac. No `ANTHROPIC_API_KEY` needed for Claude calls.
      - The Manager itself runs as a Claude Code session (long-lived) or through the Agent SDK, also on the subscription.
      - Claude compute is effectively **"unmetered" in dollars** from the user's perspective, BUT there are **subscription session limits and rate limits**. The harness must handle `rate_limit_exceeded` gracefully: exponential backoff, queueing, and surfacing "hit my limit, resuming in N minutes" to the user via the proactive channel.
      - The Manager can see its own subscription usage and surface it on the webapp dashboard (pulled from the Claude Code usage introspection, when available).
    - **Model selection:**
      - **Manager = Opus** (Claude Opus 4.6, `claude-opus-4-6`) — always. The Manager's job is reasoning about the user, routing, reflection — Opus only.
      - **Workers = Manager's choice.** The Manager is given a model-selection skill that chooses among Opus / Sonnet / Haiku per task (e.g. Haiku for log summarization, Sonnet for most coding, Opus for hard architecture work). The Manager explains its choice.
      - All model IDs centralized in one config constant so upgrades are one-line changes.
    - **Third-party APIs (non-Claude):**
      - The harness supports **pluggable third-party API keys** — initial targets: **Google Veo** (video generation), **Nano Banana / Gemini 2.5 Flash Image** (image generation). Extensible — more keys can be added without code changes.
      - Keys live in **macOS Keychain**, referenced by name in `config.toml`. Never written to disk in plaintext. Never sent to the webapp or Slack in logs.
      - Each third-party API integration is exposed to Workers as a **tool** (e.g. `generate_video`, `generate_image`) that Claude can call.
      - **Cost tracking for third-party APIs** IS needed (these are real dollars): per-key monthly ceiling, per-workflow budget, and a kill switch. Cost records go into the memory archive so the Manager can report "this month I've spent $X on Veo, $Y on Nano Banana."
    - **Kill switches:**
      - **Global kill switch** (webapp button + Slack command `/stop`) — immediately halts all Workers, pauses all Karpathy loops, stops all scheduled tasks. Manager stays online to explain what happened.
      - **Per-workflow pause** — any active Karpathy loop or long-running worker can be paused from the dashboard.

13. **Input / output modes:**
    - **Inputs (user → Manager):** text, **images** (drop a screenshot, Opus reads it via vision), **file uploads** (log files, code, docs — landed in the worker sandbox), **links** (Manager fetches and reads URLs), **screen captures** from the webapp (ad-hoc share).
    - **Outputs (Manager → user):** text, **rich formatted messages** (diffs, tables, syntax-highlighted code blocks, charts), **file attachments** (downloadable artifacts — generated files, test reports, traces), **generated images** via Nano Banana / Gemini Flash Image, **generated videos** via Google Veo.
    - **NOT supported, either direction: voice/audio.** No speech-to-text input, no TTS output. Explicitly out of scope.
    - Rich formatting must render on **both Slack and the webapp** — designed to a lowest-common-denominator message schema that both surfaces can render (Slack Block Kit on one side, React/markdown components on the other). Content model is single-source-of-truth; clients adapt.

14. **Manager persona — non-negotiable behavioral rules** (baked into the Manager's core system prompt, not user-editable at runtime):
    - **Never forget.** If the user references anything that might be in the archive — a person, a repo, a past decision, a preference, a running joke — the Manager MUST invoke `session_search` / `memory_recall` BEFORE answering. "I don't know" / "I don't remember" is disallowed unless the search has actually been run and returned empty. This is enforced by prompt discipline and a self-check skill.
    - **Never be sycophantic.** No "great question!", no empty agreement, no hedging when it has a real opinion. Disagreement is expected when warranted. The Manager should behave like a skilled collaborator who has opinions, not a customer-service bot.

15. **Manager self-modification — approved:** the Manager is permitted to edit its own code, config, and skill library as part of Karpathy L1/L2 loops. Guardrails (detailed in Security section below):
    - All self-edits go through git; every modification is a commit on a dedicated branch with a generated diff and rationale.
    - Self-edits affecting the Manager's **own running code** (not skills, not config) require a **full process restart** to take effect — the Manager cannot hot-patch itself mid-turn. Restart is a logged event.
    - Certain files are **immutable from the Manager's perspective**: Tier-2 security list, the self-modification guardrails themselves, launchd plists, Keychain access code. Edits are blocked at the filesystem layer (file mode + runtime check).
    - Every self-edit is surfaced to the user in the next proactive digest.

16. **Network / transport:** pattern is proven by OpenClaw and Hermes — a **local gateway** process runs on the Mac and bridges external clients (Slack, webapp) to the in-process Claude Code sessions.
   - **Tailscale** covers private access — webapp UI and any developer-direct access to the gateway go over the tailnet.
   - **Slack** will use **Socket Mode** (outbound websocket from the Mac to Slack's servers) so no public endpoint is needed. The Mac never opens an inbound port on the public internet.
   - **Webapp** is served from the gateway, reachable over the Tailscale hostname (mobile devices join the tailnet via Tailscale app). If public sharing is ever needed, Tailscale Funnel can expose it later — explicitly out of scope for v1.
   - **No cloud relay, no public-facing VPS.** Everything lives on the Mac + tailnet.

---

## Requirements

### Functional

**Conversational surface**
- F1. User can send text messages to the Manager from Slack (Socket Mode DM) and receive replies.
- F2. User can send text messages to the Manager from the webapp chat pane and receive replies.
- F3. Messages and read state sync bidirectionally between Slack and the webapp — a message sent/read on one surface appears on the other.
- F4. The Manager is a single persistent conversational identity, not a per-channel bot — sending from Slack and from the webapp addresses the same assistant.
- F5. User can attach images, files, and URLs to messages on both surfaces. Claude's vision and URL-fetch capabilities are available to the Manager.
- F6. Manager can reply with rich formatting (diffs, tables, syntax-highlighted code, charts) on both surfaces.
- F7. Manager can generate and return images (Nano Banana / Gemini Flash Image) and videos (Google Veo) as chat attachments.

**Memory**
- F8. Manager retains a complete, searchable archive of every user message, Manager reply, Worker transcript, tool call and result, decision, attachment, and reflection — persisted across restarts.
- F9. Manager can search its own archive via a `memory_recall` tool and receive ranked results, including structured facts/entities from the Hindsight-style layer.
- F10. Manager automatically invokes `memory_recall` whenever the user references prior work, people, preferences, or past decisions.
- F11. Manager periodically reflects during idle periods and updates the structured layer + skill library.
- F12. User can issue `/forget <topic>` or `/redact <range>` to tombstone entries. Tombstoned entries are excluded from search and context.

**Workers**
- F13. Manager can spawn in-session subagents (via `Task` tool) for short tasks that share its session budget.
- F14. Manager can spawn out-of-process Worker subprocesses via `spawn_worker_process` for long-running tasks with isolated sandboxes and independent subscription session buckets.
- F15. Workers stream status events back to the Manager via stdout JSONL; Manager routes interesting updates to the user proactively.
- F16. A Worker can be "foregrounded" — promoted to direct conversational access — and backgrounded again, with its transcript folded into Manager memory.
- F17. User can kill any Worker from the webapp dashboard or via a Slack command.

**Approvals and authority tiers**
- F18. All actions are classified as Tier 0 (autonomous), Tier 1 (approval-gated), or Tier 2 (hard-blocked).
- F19. Tier 1 actions queue an approval request delivered via Slack DM reactji and webapp button; either surface resolves the approval.
- F20. Tier 2 actions are blocked at both the Claude `PreToolUse` hook layer and the runtime tool-wrapper layer.
- F21. User can grant time-and-scope-bounded AFK autopilot (e.g. "approve all Tier 1 in repo X for 4 hours, budget $Y, nothing destructive"). Grants are logged and auto-expire.
- F22. All Tier 1 and Tier 2 decisions are logged to an audit trail.

**Proactive behavior**
- F23. Manager emits proactive messages for: worker completion, approval requests, failure alerts, idle-reflection findings, scheduled task output, opportunistic suggestions, memory-triggered reminders, morning/evening briefings.
- F24. User can configure quiet hours; non-urgent proactive messages are batched into digests during quiet hours.
- F25. Each proactive message class has a rate-limit floor to prevent spam.

**Scheduling**
- F26. User can register cron-like recurring tasks with a name, schedule, prompt, and scope.
- F27. Scheduled task runs are logged to memory and reported in the morning digest.

**Karpathy self-improvement loops**
- F28. **L2 (skills):** after each Worker task, the Manager reflects on skill performance and may write or refine a skill in the skill library git repo. Skill invocation success is tracked as a scalar metric.
- F29. **L3 (project):** user can start a project loop pointed at a specific file in a specific repo worktree with a user-provided scalar metric and time/cost budget. The loop runs Karpathy-style iterations in isolation and reports progress to the dashboard.
- F30. **L1 (user-model / prompt):** optional, user-activated. Edits the Manager's prompt-assembly code in a dedicated branch, metric = self-graded user-satisfaction signals extracted from follow-ups.
- F31. All loops run in git-tracked dedicated branches. Iterations are kept or discarded based on metric improvement. History is persisted in memory.

**Webapp**
- F32. Webapp is a static SPA served by the Gateway over Tailscale.
- F33. Panes: chat, workers, approvals, Karpathy loops, memory browser, schedules, settings. Built incrementally in that order.
- F34. Webapp is mobile-responsive; first-class on mobile Safari.
- F35. Webapp is a pure client of the Gateway's WebSocket — no direct connection to the Manager.

**Third-party integrations**
- F36. Third-party API keys (Veo, Nano Banana, etc.) are stored in the macOS Keychain and referenced by name from `config.toml`.
- F37. Each third-party tool tracks per-key monthly spend, per-workflow budget, and has a kill switch.
- F38. Manager can see and report its own third-party spend.

**Self-modification**
- F39. Manager can edit its own skills and configuration via a guarded `self_modify` tool.
- F40. Self-edits go through git commits on a dedicated branch with a generated diff and rationale.
- F41. Edits to Manager's running Python code require a full process restart; Manager cannot hot-patch itself mid-turn.
- F42. Protected files (Tier-2 list, self-mod guardrails, launchd plists, Keychain access code) are immutable from the Manager's perspective, enforced at filesystem and runtime layers.
- F43. Every self-edit is surfaced in the next proactive digest.

### Non-functional

**Reliability**
- N1. Gateway restarts do not lose queued inbound messages (SQLite WAL durability).
- N2. Manager restarts do not drop Gateway connections or webapp websockets.
- N3. After a full host reboot, both services come up automatically via `launchd` and the Manager resumes from its last memory state.
- N4. All queue operations are at-least-once with idempotency keys; duplicate delivery is recognized and ignored.
- N5. Manager session rate-limit exhaustion is handled with exponential backoff and user notification; no silent stalls.

**Performance (qualitative — no hard latency SLAs for v1)**
- N6. Round-trip latency for a simple text reply should feel conversational on Slack (Manager reply begins streaming within a few seconds of message receipt in the common case).
- N7. Memory search returns results within seconds on a 1 GB archive on SSD.
- N8. Webapp chat pane remains responsive with 1000+ message history via virtualized rendering.

**Security**
- N9. No secret ever written to `config.toml`, logs, or memory archive in plaintext.
- N10. No inbound ports opened on the public internet. All external access via Slack Socket Mode (outbound) and Tailscale (private).
- N11. Manager and Workers cannot write outside the sandbox + allowlisted repo roots.
- N12. Tier-2 hard blocks are enforced at two independent layers (hook + runtime).
- N13. The Manager's personal config directory is isolated from the user's daily Claude Code config.

**Observability**
- N14. Every inbound message, outbound reply, tool call, and approval decision is logged to the audit trail.
- N15. Per-tool cost and per-workflow cost are visible on the dashboard.
- N16. Subscription session usage (rate-limit headroom) is visible on the dashboard when the Claude SDK exposes it.
- N17. Gateway and Manager each write structured logs to `~/Library/Application Support/Interceder/logs/`.

**Portability & upgrade**
- N18. All Claude/model IDs live in one config module; upgrades are one-line changes.
- N19. The memory layer is behind a Python interface; swapping SQLite for another backend is a bounded change.
- N20. Updating the harness code is `git pull` + `launchctl kickstart` with no manual migration in the common case; schema changes use a forward-only migration runner.

**Privacy**
- N21. Memory archive is append-only by default; tombstoning is an explicit, logged operation.
- N22. No telemetry leaves the Mac. Nothing is sent to third parties except (a) Claude calls via the Agent SDK, (b) explicit Slack messages the user directed, (c) explicit Veo/Nano Banana API calls the Manager made.

---

## Architecture

**Chosen approach: two-process split — Gateway + Manager Supervisor, with Worker subprocesses spawned by the Manager.**

Hermes-as-substrate (Approach 3) was rejected because the user's Claude Code Max subscription authenticates through the `claude` CLI / Agent SDK, not through an OpenAI-style API endpoint that Hermes's pluggable model layer expects. Using Hermes would force either paying API rates (defeating the subscription) or building a fragile shim. A custom monolith (Approach 1) was rejected because Claude Code sessions have unpredictable lifecycles (rate limits, restarts) — a thin always-up Gateway keeps Slack and the webapp connected through any Manager restart.

### Process topology

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│        Gateway          │         │       Manager Supervisor     │
│  (Python, always up)    │ ──────► │  (Python, wraps Agent SDK)   │
│                         │  local  │                              │
│  • Slack Socket Mode    │  queue  │  • Owns the long-lived       │
│  • FastAPI + WS webapp  │ (SQLite │    Claude Code Manager       │
│  • Auth / session       │   WAL)  │    session (Agent SDK)       │
│  • Message schema       │         │  • Hot/cold memory curation  │
│  • Rich-render adapter  │         │  • Worker subprocess mgmt    │
│  • Static webapp build  │         │  • Skill library + reflection│
│                         │         │  • Scheduler + approvals     │
└─────────────────────────┘         └──────────────┬───────────────┘
                                                   │ spawns
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │  Worker processes (N)        │
                                    │  Each = a `claude` CLI /     │
                                    │  Agent SDK session on the    │
                                    │  SAME Max subscription,      │
                                    │  own sandbox dir, own task.  │
                                    └──────────────────────────────┘
```

### Why two processes, not one

1. **Rate-limit recovery.** Max-subscription sessions will hit limits. The Gateway stays up and queues user messages to disk; when the Manager recovers, it drains the queue. No dropped messages, no disconnected clients.
2. **Manager restartability.** Manager restarts (crashes, upgrades, memory-cycle events, Agent SDK session refreshes) do not affect the Gateway's Slack socket or active webapp websockets.
3. **Single supervision locus for Claude compute.** Manager and Workers share one subscription, one sandbox scheme, one memory layer — collocating them in one process makes reasoning about usage and safety simpler.
4. **Free audit log.** The Gateway↔Manager queue IS the canonical record of every inbound user message, outbound Manager reply, and approval decision — replay-able, inspectable, a first-class observability tool.

### Key technical note — the Manager is a wrapper, not a reimplementation

The Manager Supervisor is Python code that **wraps** a long-lived Claude Agent SDK session. The SDK session performs all Claude reasoning on the user's Max subscription. The Supervisor's job is to:

- Own the hot memory and inject it into the Manager session's system prompt as turns progress.
- Expose memory, Veo, Nano Banana, Worker-spawn, and other custom tools to the Manager session via the Agent SDK's tool-registration interface.
- Consume the Gateway's inbound queue, translate each user message into a turn on the Manager session, and stream the reply back.
- Supervise Worker subprocesses (each also a Claude Agent SDK session) and route their reports back into the Manager session's tool results.
- Curate cold memory (the Hermes-style SQLite+FTS5 archive) outside the Manager session so the session's context stays small.

This design keeps ALL Claude compute on the Max subscription through the official SDK — no API key juggling, no secondary billing.

---

## Components

Nine independently-reasoned units. Each has one purpose and a defined interface.

### Claude Code inheritance (foundational)

The Manager and every Worker are **Claude Agent SDK sessions** on the user's Max subscription. They inherit Claude Code's native extensibility **for free**:

- **Skills** — markdown-frontmatter skills auto-discovered from a configured skill directory. The Manager can invoke skills via the `Skill` tool. **We do not reimplement a skill system.**
- **Self-authored skills** — Claude Code's native `writing-skills` meta-skill already lets Claude create new skills mid-task. Karpathy L2 is mostly an orchestration layer over this existing mechanic (metric tracking + reflection triggers), not a rebuild.
- **MCP plugins** — any MCP server in the Interceder Claude config is available as a tool. **Before writing any custom tool (Veo, Nano Banana, GitHub, etc.), we check for an existing MCP server and prefer that.**
- **Hooks** — `PreToolUse`, `PostToolUse`, `SessionStart`, etc. from `settings.json`. Used for Tier-2 enforcement, post-task memory reflection triggers, and metric emission.
- **Slash commands / user-invocable skills** — `/forget`, `/stop`, `/afk` and friends are implemented as user-invocable skills, invocable from Slack.
- **CLAUDE.md** — each Worker's sandbox dir can include a per-repo `CLAUDE.md` for repo-specific behavior.
- **Subagents** via `Task` tool — available for short in-session subtasks.

**Isolated Claude config:** the Interceder Manager and Workers use a dedicated config directory (`~/Library/Application Support/Interceder/claude-config/`) — NOT the user's personal `~/.claude/`. This isolates Interceder's skills, plugins, hooks, and settings from the user's daily Claude Code usage. No bleed-through in either direction.

### 1. Gateway (`interceder-gateway`)
**Purpose:** The always-up I/O front door. Knows nothing about Claude.
**Runs as:** `launchd` service, Python (FastAPI + `slack_bolt` in socket mode).
**Interfaces:**
- Slack Socket Mode client (outbound websocket).
- FastAPI HTTP + WebSocket server (serves webapp static bundle and the webapp live-update socket).
- SQLite-backed `inbox` / `outbox` queue (WAL mode) as durable handoff to the Manager Supervisor.
- **No LLM calls. No memory access. No tool execution.**
**Responsibilities:** normalize inbound events into a single `Message` schema; authenticate (tailnet + Slack user ID); enforce per-user rate limiting; render Manager outbound messages into Slack Block Kit / webapp WS-JSON; manage approval reaction callbacks.

### 2. Manager Supervisor (`interceder-manager`)
**Purpose:** The brain. Owns the long-lived Manager Agent SDK session, the memory layer, and all Workers.
**Runs as:** `launchd` service, Python, wraps `claude-agent-sdk`.
**Interfaces:**
- Drains the Gateway's `inbox` queue, writes replies to `outbox`.
- Owns one `ClaudeAgentSession` pointing at the Interceder Claude config — the long-lived Opus Manager. Created on startup, preserved until intentional restart.
- Registers custom tools on the Manager session beyond those provided by Claude Code: `memory_recall`, `memory_write`, `spawn_worker_process`, `approve_or_queue`, `schedule_task`, `start_karpathy_loop`, `self_modify` (with guardrails), plus read-only introspection. All Claude-Code-native tools (skills, Task, Read, Edit, MCP tools) continue to work.
- Background memory curation loop runs during idle periods.
**Responsibilities:** preserve Manager continuity across restarts, supervise Workers, own all writes to the memory archive, enforce tiered approvals before dispatching, handle rate-limit backoff on the Manager session.

### 3. Workers — two-tier model
- **In-session subagents** (via Claude Code's `Task` tool + `subagent_type`) — short, well-bounded tasks. Share the Manager session's budget. Cheap and fast. Used for "summarize this file," "explore these three paths," "run one test pass."
- **Out-of-process Worker subprocesses** (via `spawn_worker_process` custom tool) — long-running tasks in their own Agent SDK session on a separate subscription session bucket. Used for multi-minute to multi-hour work: implementation tasks, test suites, Karpathy loop runs. Each has its own sandbox dir, own tool scope (reduced — no `self_modify`, no `schedule_task`), and reports status events via stdout JSONL.
- The Manager picks which tier per task and explains its choice.

### 4. Memory Layer (library)
- **SQLite DB** (`memory.sqlite`) — FTS5 full-text search on messages, transcripts, decisions, facts. Tables for schedules, approvals, audit, cost tracking.
- **Blob store** (`blobs/sha256/...`) — content-addressed attachments.
- **Skill library** — **a git repo at `claude-config/skills/`, configured as a Claude Code skill directory**. Skills are native Claude Code skills; git history is the skill evolution log.
- **Structured layer** — entity/fact/relationship/reflection tables, populated by a background extraction job.
- **Interface (Python):** `Memory.recall(query, scope)`, `Memory.write(entry, kind)`, `Memory.promote(id)`, `Memory.tombstone(id)`, `Memory.reflect()`.

### 5. Approval + Audit System (library, with hook integration)
**Purpose:** Tiered action gating and audit log.
**Interface:** `Approval.check(action, context) → Allow | NeedsApproval | Blocked`.
**Enforcement layers:**
- **Claude Code `PreToolUse` hook** — first line of defense, fires before any tool call, short-circuits blocked actions without involving the Manager.
- **Runtime check in tool wrappers** — second line, catches anything that slips past the hook.
- **Filesystem-level** — file modes and writable-root restrictions.
**Approval flow:** `NeedsApproval` queues the action, sends a proactive message through the Gateway, waits for ✅/❌, resumes or rejects.

### 6. Scheduler (library)
**Interface:** `Scheduler.register(name, cron, prompt, scope)`, `Scheduler.tick()`.
**Storage:** `schedules` table in `memory.sqlite`. On trigger, synthesizes a `[scheduled:name]` message into the Manager's inbox.

### 7. Self-Improvement Loops (three modules sharing a core primitive)
All three layer on top of a shared `KarpathyLoop` core: single editable asset, scalar metric, time-boxed cycle, keep-or-discard.
- **L1 — user-model / prompt loop** — edits the Manager's prompt assembly code in a dedicated branch. Metric = self-graded user-satisfaction signals from follow-up messages. **v1 status: disabled by default, user opt-in per session.**
- **L2 — skills loop** — edits skills in the skill library git repo. Metric = self-graded task success rate tagged by skill invocation. Built on Claude Code's `writing-skills` meta-skill. **v1 status: enabled from day one.**
- **L3 — project loop** — pointed at a Worker-managed codebase with a user-provided scalar metric. Runs experiments in a dedicated worktree. **v1 status: disabled by default, user activates per-project with scalar metric and time/cost budget.**

### 8. Webapp (`interceder-web`)
Static SPA served by the Gateway. React (or SolidStart). Connects to Gateway WebSocket for live updates.
Panes (built incrementally in this order): **chat → workers → approvals → memory → Karpathy loops → schedules → settings.** Mobile-friendly / responsive is a v1 requirement.

### 9. Tool integrations
Preference order: (1) existing MCP server, (2) Claude Code native tool, (3) custom `Tool` implementation.
Initial tools beyond Claude Code's defaults:
- **Google Gemini image / video** (Nano Banana + Veo) — check for MCP-google-genai first; fall back to custom if none.
- **Memory tools** — `memory_recall`, `memory_write`, `memory_reflect` — always custom.
- **Worker spawning** — `spawn_worker_process` — always custom.
- **Karpathy loop control** — `start_karpathy_loop`, `report_iteration`, `get_best` — always custom.
- **Self-modification** — `self_modify` — always custom with hard guardrails.
- **GitHub, filesystem, fetch, shell** — MCP servers preferred, custom only if needed.
All custom tools track cost, rate-limit, and reference secrets via Keychain.

---

## Data flow

Five canonical scenarios. Each walks through the components described above.

### Scenario A — Simple text turn from Slack

```
  User types "hey, what's the status on that refactor?" in Slack DM
            │
            ▼
  Slack sends event over Socket Mode websocket
            │
            ▼
  Gateway receives event
    • authenticates (Slack user ID matches configured user)
    • normalizes to Message{id, user_id, source:"slack", content, attachments}
    • writes row to `inbox` table (WAL-durable)
    • acks Slack
            │
            ▼
  Manager Supervisor's inbox-drain loop picks up the row
    • marks it "in_flight" with its process PID
    • assembles the turn:
        - hot memory (Manager identity, active-task context, pinned facts, recent turns)
        - the new user message
    • injects a discipline reminder from the "never forget" self-check skill:
      "Before answering, consider if this references prior work. If yes, call memory_recall."
            │
            ▼
  Manager session (Claude Agent SDK) runs the turn
    • decides "refactor" is a reference to prior work
    • calls memory_recall(query="refactor status", scope=recent)
    • Memory Layer runs FTS5 search + structured entity lookup
    • returns ranked results: worker IDs, task summaries, timestamps
    • Manager reads context, formulates answer
            │
            ▼
  Manager replies with streaming text
    • Supervisor pipes stream → writes each chunk to `outbox` table
    • each chunk carries the original inbox row's idempotency key
            │
            ▼
  Gateway's outbox-drain loop picks up chunks
    • renders to Slack Block Kit (and webapp WS-JSON in parallel)
    • streams chunks back to Slack → user sees typed reply
    • also broadcasts to all connected webapp websockets
            │
            ▼
  Turn complete
    • Supervisor appends full turn (user + assistant) to `messages` table
    • if attachments, writes blobs to content-addressed store
    • marks inbox row "completed", updates audit log
```

### Scenario B — Manager spawns a Worker subprocess

```
  User: "Go implement the new search bar in ~/code/dashboard, open a PR when done"
            │
            ▼ (same path as Scenario A through memory_recall)
  Manager session decides this is multi-step work warranting a separate process
    • picks model: Sonnet (routine coding)
    • calls spawn_worker_process(task_spec={
        goal: "...", working_dir: "~/code/dashboard",
        allowed_tools: ["Read","Edit","Bash","Grep","Glob","Task"],
        model: "claude-sonnet-4-6",
        time_budget: "45min", cost_budget: null  # covered by subscription
      })
            │
            ▼
  Supervisor's spawn_worker_process tool handler
    • Approval.check(action="spawn_worker", context=...)  → Tier 0, allowed
    • creates worker sandbox symlink into allowlisted repo dir
    • fork+exec: `python -m interceder.worker --task-spec ...`
    • Worker process initializes its own Agent SDK session on the same subscription
    • Supervisor records worker in `workers` table; status="running"
    • Supervisor subscribes to worker's stdout JSONL stream
            │
            ▼
  Worker runs autonomously
    • Each tool call the worker makes → JSONL event to stdout
    • Supervisor parses each event:
        - if "file_edited": snapshot + record in memory
        - if "test_passed" / "test_failed": record metric event
        - if "progress": update `workers` table status
        - if "needs_approval": convert to approval request, bubble up
    • Supervisor streams "worker update" events to the Gateway's outbox
      (which relays to the webapp's live-workers pane)
            │
            ▼
  Worker completes
    • final event: "done" with summary + diff ref
    • Supervisor folds the transcript into the memory archive
    • Supervisor injects a turn into the Manager session:
      "Worker ${id} completed: ${summary}. Pending action: open PR?"
    • Manager decides whether to emit a proactive "worker done" ping to the user
      (rate-limited per proactive-class rules)
            │
            ▼
  Proactive ping goes out
    • Supervisor writes a proactive message to `outbox` with source="manager_proactive"
    • Gateway delivers to Slack DM AND webapp inbox
```

### Scenario C — Tier-1 approval gate (e.g. `git push`)

```
  Worker wants to run `git push origin feature-search-bar`
            │
            ▼
  PreToolUse hook fires BEFORE the actual bash call reaches the shell
    • hook invokes Approval.check(action="shell:git_push", context={repo, branch})
    • returns NeedsApproval
    • hook blocks the tool call with a structured response:
      { "decision": "deny", "reason": "queued for approval: ${approval_id}" }
  Worker receives the denial, reports up via status event
            │
            ▼
  Supervisor's approval queue persists the request in `approvals` table
    • creates a proactive message with action details + ✅/❌ buttons
    • writes to outbox (Slack + webapp)
            │
            ▼
  User taps ✅ in Slack (or webapp button)
    • Gateway captures the reaction event, looks up approval_id
    • updates `approvals` row: status=approved, resolved_by=slack, at=timestamp
    • writes an "approval_resolved" event into the Manager's inbox
            │
            ▼
  Manager session picks up the resolution
    • re-invokes the Worker's blocked action via spawn_worker_process (resume mode)
      OR tells the Worker (if still alive) to retry with approval_id=X
    • Worker's PreToolUse hook sees approval_id=X in context → allows the push
```

### Scenario D — Scheduled task

```
  Config: "every weekday 9am, triage GitHub issues on dashboard repo"
            │
            ▼
  Scheduler.tick() runs every minute in the Manager Supervisor
    • reads `schedules` table
    • finds one matching now → loads prompt + scope
    • writes a synthetic message into Manager's inbox:
      Message{source="scheduler:daily-triage", content="<scheduled prompt>"}
            │
            ▼
  Manager handles it identically to a user message
    • may spawn a Worker
    • proactive result goes to morning digest if quiet hours,
      immediate ping otherwise
```

### Scenario E — Karpathy L3 project loop

```
  User: "Start an L3 loop on ~/code/trading-bot/src/strategy.py,
         metric = 5-min walk-forward sharpe ratio, budget = 2 hours"
            │
            ▼
  Manager validates the request (file exists, metric is defined, budget reasonable)
    • Approval.check(action="start_karpathy_loop", tier=Tier 1)
    • user already granted AFK autopilot for this repo → auto-approved, logged
            │
            ▼
  Manager calls start_karpathy_loop(config=...)
    • Supervisor creates a dedicated git worktree for the loop:
      ~/interceder-workspace/karpathy/trading-bot-L3-20260409/
    • writes loop state to `karpathy_loops` table: config, best, iterations=0
    • spawns a dedicated Worker subprocess in loop mode
            │
            ▼
  Loop iteration cycle (inside the Worker subprocess):
    1. Read current strategy.py, generate N candidate edits (Sonnet)
    2. For each candidate:
        - apply edit to the single editable asset
        - run time-boxed backtest (the scalar metric)
        - keep result if > best, else discard
    3. Commit keeps to the loop's branch with rationale
    4. Emit "iteration complete" event to parent Supervisor
    5. Supervisor updates `karpathy_loops` + webapp dashboard chart
    6. Loop until budget exhausted
            │
            ▼
  Loop completes (or is paused by kill switch)
    • final report written to memory
    • proactive ping: "Loop done. Best sharpe: X.XX (up from Y.YY). Diff: ..."
```

### Message schema (canonical, single source of truth)

All messages across queue boundaries conform to this schema:

```python
@dataclass
class Message:
    id: str                    # UUID, idempotency key
    correlation_id: str        # groups related messages (thread)
    user_id: str               # "me" in v1, seam for future
    source: Literal["slack", "webapp", "scheduler:*",
                    "manager_proactive", "worker_event", "approval"]
    kind: Literal["text", "tool_result", "attachment",
                  "approval_request", "approval_resolution",
                  "worker_update", "proactive"]
    content: str               # markdown
    attachments: list[AttachmentRef]  # blob hashes + metadata
    metadata: dict             # source-specific fields
    created_at: datetime
    processed_at: datetime | None
```

Clients (Slack Block Kit renderer, webapp React components) adapt from this canonical shape.

---

## Memory schema

### SQLite tables (in `memory.sqlite`, WAL mode)

```sql
-- core message log, the spine of everything
CREATE TABLE messages (
  id              TEXT PRIMARY KEY,        -- UUID = idempotency key
  correlation_id  TEXT NOT NULL,           -- threads related messages
  user_id         TEXT NOT NULL DEFAULT 'me',
  source          TEXT NOT NULL,           -- slack|webapp|scheduler:*|manager_proactive|worker_event|...
  kind            TEXT NOT NULL,           -- text|tool_result|attachment|approval_*|worker_update|proactive
  role            TEXT NOT NULL,           -- user|assistant|tool|system
  content         TEXT NOT NULL,           -- markdown
  metadata_json   TEXT NOT NULL,           -- source-specific JSON
  tombstoned_at   INTEGER,                 -- unix ts, NULL = live
  created_at      INTEGER NOT NULL
);
CREATE INDEX idx_messages_correlation ON messages(correlation_id, created_at);
CREATE INDEX idx_messages_created ON messages(created_at);

-- full-text search over message content
CREATE VIRTUAL TABLE messages_fts USING fts5(
  content, source, kind, content='messages', content_rowid='rowid'
);
-- triggers keep fts in sync with messages
CREATE TRIGGER messages_ai AFTER INSERT ON messages BEGIN
  INSERT INTO messages_fts(rowid, content, source, kind)
  VALUES (new.rowid, new.content, new.source, new.kind);
END;
CREATE TRIGGER messages_ad AFTER DELETE ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, content, source, kind)
  VALUES ('delete', old.rowid, old.content, old.source, old.kind);
END;
CREATE TRIGGER messages_au AFTER UPDATE ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, content, source, kind)
  VALUES ('delete', old.rowid, old.content, old.source, old.kind);
  INSERT INTO messages_fts(rowid, content, source, kind)
  VALUES (new.rowid, new.content, new.source, new.kind);
END;

-- content-addressed blob metadata (screenshots, file snapshots, generated media)
CREATE TABLE blobs (
  sha256          TEXT PRIMARY KEY,
  byte_size       INTEGER NOT NULL,
  mime_type       TEXT NOT NULL,
  origin          TEXT NOT NULL,          -- user_upload|worker_snapshot|nano_banana|veo|screenshot
  created_at      INTEGER NOT NULL
);

-- attachments link messages to blobs (many-to-many)
CREATE TABLE attachments (
  message_id      TEXT NOT NULL REFERENCES messages(id),
  sha256          TEXT NOT NULL REFERENCES blobs(sha256),
  label           TEXT,
  PRIMARY KEY (message_id, sha256)
);

-- structured long-term layer (Hindsight-style)
CREATE TABLE entities (
  id              INTEGER PRIMARY KEY,
  name            TEXT NOT NULL,
  kind            TEXT NOT NULL,          -- person|repo|project|concept|tool|skill|...
  properties_json TEXT NOT NULL,
  first_seen_msg  TEXT REFERENCES messages(id),
  last_seen_at    INTEGER NOT NULL
);
CREATE UNIQUE INDEX idx_entities_name_kind ON entities(name, kind);

CREATE TABLE facts (
  id              INTEGER PRIMARY KEY,
  entity_id       INTEGER REFERENCES entities(id),
  claim           TEXT NOT NULL,          -- "prefers tabs", "works at X", "uses Vim"
  confidence      REAL NOT NULL,          -- 0.0-1.0
  source_msg_id   TEXT REFERENCES messages(id),
  extracted_at    INTEGER NOT NULL,
  superseded_by   INTEGER REFERENCES facts(id)  -- NULL = current
);

CREATE TABLE relationships (
  id              INTEGER PRIMARY KEY,
  subject_id      INTEGER NOT NULL REFERENCES entities(id),
  predicate       TEXT NOT NULL,          -- "works_on", "depends_on", "authored_by"
  object_id       INTEGER NOT NULL REFERENCES entities(id),
  confidence      REAL NOT NULL,
  source_msg_id   TEXT REFERENCES messages(id),
  extracted_at    INTEGER NOT NULL
);

CREATE TABLE reflections (
  id              INTEGER PRIMARY KEY,
  kind            TEXT NOT NULL,          -- task_retro|periodic|skill_evaluation|loop_summary
  scope_json      TEXT NOT NULL,          -- what this reflection is about
  content         TEXT NOT NULL,          -- the reflection itself
  source_msg_ids  TEXT NOT NULL,          -- JSON array of contributing message IDs
  created_at      INTEGER NOT NULL
);

-- hot memory: curated pinned items always in the Manager's context
CREATE TABLE hot_memory (
  id              INTEGER PRIMARY KEY,
  slot            TEXT NOT NULL,          -- identity|active_task|pinned_facts|recent_turns|...
  content         TEXT NOT NULL,
  priority        INTEGER NOT NULL,       -- eviction ordering
  token_estimate  INTEGER NOT NULL,
  last_touched_at INTEGER NOT NULL
);

-- workers: one row per spawned subprocess Worker
CREATE TABLE workers (
  id              TEXT PRIMARY KEY,       -- UUID
  parent_id       TEXT,                   -- Manager session ID or parent worker
  task_spec_json  TEXT NOT NULL,
  status          TEXT NOT NULL,          -- queued|running|done|failed|killed
  model           TEXT NOT NULL,
  sandbox_dir     TEXT NOT NULL,
  pid             INTEGER,
  started_at      INTEGER,
  ended_at        INTEGER,
  summary         TEXT,
  transcript_path TEXT                    -- path under workers/
);

CREATE TABLE worker_events (
  id              INTEGER PRIMARY KEY,
  worker_id       TEXT NOT NULL REFERENCES workers(id),
  event_kind      TEXT NOT NULL,          -- tool_call|tool_result|progress|needs_approval|done|error
  payload_json    TEXT NOT NULL,
  created_at      INTEGER NOT NULL
);

-- approvals: tier-1 requests pending or resolved
CREATE TABLE approvals (
  id              TEXT PRIMARY KEY,       -- UUID
  action          TEXT NOT NULL,
  context_json    TEXT NOT NULL,
  tier            INTEGER NOT NULL,
  status          TEXT NOT NULL,          -- pending|approved|denied|expired
  requested_by    TEXT NOT NULL,          -- manager|worker:<id>
  resolved_by     TEXT,                   -- slack|webapp|afk_grant
  resolved_at     INTEGER,
  expires_at      INTEGER NOT NULL,
  created_at      INTEGER NOT NULL
);

-- AFK autopilot grants
CREATE TABLE afk_grants (
  id              TEXT PRIMARY KEY,
  scope_json      TEXT NOT NULL,          -- repos, budget, action allowlist
  granted_at      INTEGER NOT NULL,
  expires_at      INTEGER NOT NULL,
  revoked_at      INTEGER
);

-- immutable audit trail
CREATE TABLE audit_log (
  id              INTEGER PRIMARY KEY,
  actor           TEXT NOT NULL,          -- manager|worker:<id>|user|scheduler|system
  action          TEXT NOT NULL,
  tier            INTEGER NOT NULL,
  outcome         TEXT NOT NULL,          -- allow|approved|denied|blocked|error
  context_json    TEXT NOT NULL,
  created_at      INTEGER NOT NULL
);

-- scheduler
CREATE TABLE schedules (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  cron_expr       TEXT NOT NULL,
  prompt          TEXT NOT NULL,
  scope_json      TEXT NOT NULL,
  enabled         INTEGER NOT NULL DEFAULT 1,
  last_run_at     INTEGER,
  next_run_at     INTEGER NOT NULL,
  created_at      INTEGER NOT NULL
);

-- Karpathy loop state
CREATE TABLE karpathy_loops (
  id              TEXT PRIMARY KEY,
  layer           TEXT NOT NULL,          -- L1|L2|L3
  editable_asset  TEXT NOT NULL,          -- file path or git ref
  metric_name     TEXT NOT NULL,
  metric_definition_json TEXT NOT NULL,
  branch          TEXT NOT NULL,
  worktree        TEXT,                   -- for L3
  status          TEXT NOT NULL,          -- running|paused|done|failed
  best_score      REAL,
  iterations      INTEGER NOT NULL DEFAULT 0,
  budget_json     TEXT NOT NULL,          -- time + cost limits
  started_at      INTEGER NOT NULL,
  ended_at        INTEGER
);

CREATE TABLE karpathy_iterations (
  id              INTEGER PRIMARY KEY,
  loop_id         TEXT NOT NULL REFERENCES karpathy_loops(id),
  iteration       INTEGER NOT NULL,
  commit_hash     TEXT NOT NULL,
  metric_value    REAL NOT NULL,
  kept            INTEGER NOT NULL,       -- 0/1
  rationale       TEXT NOT NULL,
  wall_seconds    INTEGER NOT NULL,
  created_at      INTEGER NOT NULL
);

-- cost tracking for third-party APIs (Claude is covered by Max subscription)
CREATE TABLE costs (
  id              INTEGER PRIMARY KEY,
  tool            TEXT NOT NULL,          -- veo|nano_banana|other
  key_name        TEXT NOT NULL,          -- Keychain reference name
  workflow_id     TEXT,                   -- optional: ties to worker or loop
  usd_cents       INTEGER NOT NULL,
  units_json      TEXT NOT NULL,          -- tokens, seconds, images, etc.
  created_at      INTEGER NOT NULL
);

-- schema version marker for forward-only migrations
CREATE TABLE schema_meta (
  version         INTEGER PRIMARY KEY,
  applied_at      INTEGER NOT NULL
);
```

### Blob store layout

```
~/Library/Application Support/Interceder/blobs/sha256/
├── aa/
│   └── aabbccdd...ff        # raw blob, filename = full sha256
├── bb/
...
```

Two-level fanout by the first two hex chars to keep any single directory under ~65k entries. Files are never rewritten; duplicates are no-ops (same hash → same content).

### Skill library layout

```
~/Library/Application Support/Interceder/claude-config/skills/
├── .git/                    # skill evolution history
├── memory/
│   └── session_search.md    # the "knows to search" discipline skill
├── workflows/
│   └── commit_and_pr.md     # reusable workflow skills
├── meta/
│   └── task_reflection.md   # post-task reflection routine, drives L2
└── ...
```

Every skill is a standard Claude Code skill (markdown with frontmatter: `name`, `description`, optional `when_to_use`, body). The directory is registered as a skill source in the Interceder Claude config's `settings.json`.

### Memory layer interface (Python, abbreviated)

```python
class Memory:
    def recall(self, query: str, *, scope: Scope, limit: int = 10) -> list[Recall]: ...
    def write(self, entry: MemoryEntry) -> str: ...              # returns id
    def attach(self, message_id: str, blob_bytes: bytes, mime: str) -> str: ...
    def reflect(self, scope: Scope) -> Reflection: ...           # background job
    def hot(self) -> HotContext: ...                             # rendered hot memory
    def promote(self, entry_id: str, slot: str, priority: int) -> None: ...
    def demote(self, hot_id: int) -> None: ...
    def tombstone(self, query: str | str_range) -> int: ...      # returns count
    def search_entities(self, name: str, kind: str | None = None) -> list[Entity]: ...
    def add_fact(self, entity_id: int, claim: str, source_msg_id: str) -> int: ...
```

The Manager session calls these via custom tools registered on the Agent SDK; direct Python calls from Supervisor bypass tool overhead for internal maintenance.

---

## Security model

### Tier 0 — autonomous (no approval)
- Reads of any allowlisted path.
- Writes to the Worker sandbox root (`~/interceder-workspace/`).
- Writes to the current Worker's own subdirectory.
- Writes to allowlisted repo roots, **but only to feature branches** (see Tier 1 for protected branches).
- Running tests, local builds, lint/format tools inside the sandbox or an allowlisted repo.
- Running `git add`, `git commit`, `git branch`, `git checkout` on non-protected branches.
- Writes to the memory archive.
- Spawning Workers.
- Calling `memory_recall`, `memory_write`, `skill_invoke`, `schedule_task`.
- Idle-time reflection, hot-memory promotion/demotion.
- Fetching public URLs (no credentials attached).
- Calling MCP tools registered in the Interceder Claude config, **except** those explicitly marked Tier 1 in settings.

### Tier 1 — approval-gated
- `git push` (any branch), `git push --force` (any non-protected branch).
- Merging PRs, closing PRs, force-pushing feature branches.
- Adding a new path to the allowlist.
- Installing global packages (`brew install`, `npm install -g`, `pip install --user`, `uv tool install`).
- Running DB migrations or any command marked as destructive in the tool registry.
- Any HTTP call that costs money (Veo, Nano Banana, any Stripe/payment API).
- Sending Slack messages to any workspace/channel that is not the user's own configured DM channel.
- Starting a Karpathy L3 loop with a budget above a configurable ceiling.
- Starting the Karpathy L1 (user-model) loop at all — requires explicit session-scoped user approval.
- Writing to a file outside the sandbox and allowlisted repo roots.
- Any action annotated `tier=1` in the tool registry (extensibility seam).

### Tier 2 — hard-blocked
**These are never allowed. Enforced at both the `PreToolUse` hook layer and the runtime tool-wrapper layer. Both layers must agree; disagreement logs a critical audit event and blocks.**

- `rm -rf /` or `rm -rf ~` or anything `rm`-based targeting a path outside the sandbox.
- `git push --force` to `main`, `master`, `prod`, `production`, `release`, `release/*` on any allowlisted repo.
- Any `git push` to `main`, `master`, `prod`, `production` — these require normal (non-force) push to go through Tier 1 approval; force-push to them is Tier 2 forever.
- Writes to anything under `~/.ssh/` (reading public keys is allowed).
- Any access to `~/Library/Keychains/`, `~/.config/gh/hosts.yml`, credential stores of any kind.
- Writes to launchd plists for `com.interceder.gateway` or `com.interceder.manager`.
- Modifications to the Tier-2 list itself (in code or config).
- Modifications to the self-modification guardrail code.
- Disabling the Claude `PreToolUse` security hook.
- Sending email, SMS, or any telephony message. (v1 has no email/SMS integration; this is a hard block against future regressions.)
- Calling any payment/banking API (Stripe, Plaid, ACH, card processors). No payment capability is installed in v1; this is a standing prohibition.
- Reading or writing other users' home directories.
- Mounting or unmounting volumes, modifying disk partitions, running `diskutil` destructively.
- Executing binaries downloaded at runtime unless explicitly whitelisted at install time.
- Writing to files owned by `root` or in `/System/`, `/usr/` (except `/usr/local/`), `/private/etc/`.
- Disabling or modifying any `launchd` service not owned by Interceder.

### Approval flow detail
1. A tool call is issued by the Manager or a Worker.
2. The `PreToolUse` hook runs `Approval.check(action, context)`. If `Blocked`, hook denies with a structured reason; audit logs the block.
3. If `NeedsApproval`: hook denies the tool call immediately with `{decision:"deny", reason:"queued:${approval_id}"}`. The approval row is created with `status=pending`, `expires_at=now+4h` (default).
4. Supervisor emits a proactive approval message to the Gateway's outbox.
5. Gateway delivers the approval to both Slack (DM with ✅/❌ reactji) and the webapp (inbox item with buttons).
6. When the user resolves the approval on either surface, the Gateway captures the event, atomically updates the `approvals` row, and writes an `approval_resolved` message to the Manager's inbox.
7. Manager handles the resolution: if approved, it re-invokes the action (fresh call, with the approval ID in context so the hook allows it); if denied, it notes the denial and adjusts plan.
8. Expired approvals auto-deny after their `expires_at` and the Manager is notified.

### AFK mode
- Scope: repo(s), tier(s) to auto-approve, action allowlist/denylist, budget ceiling for any paid tools, duration.
- Scoped grants are written to `afk_grants`. `Approval.check` consults active grants after computing the base decision: if a pending Tier-1 action matches an active grant's scope and predicate, it auto-approves.
- Tier-2 is never affected by AFK grants.
- Every AFK grant and every auto-approval under a grant is logged to `audit_log`.
- Grants auto-expire; the Manager warns the user when one is about to expire if there's pending work depending on it.

### Self-modification guardrails
- The `self_modify` tool is only registered on the Manager session, never on Workers.
- Every call creates a git commit on a dedicated branch named `self-mod/<timestamp>-<short-desc>`.
- Edits to files in the protected set (enumerated in code) are rejected at the tool layer AND at filesystem layer (files are chmod'd to owner-only, and the tool checks a deny-list before opening).
- Edits to Manager Python code require `launchctl kickstart` of the `interceder-manager` service to take effect. The tool schedules this restart with a confirmation-delay window so the user has a chance to read the diff first.
- Edits to skills and non-code config take effect immediately on next invocation (skills are re-read each use).
- Every self-edit is surfaced in the next proactive digest with the diff, the rationale, and a one-click rollback button.

### Secrets
- All secrets (Slack bot/app tokens, Veo key, Nano Banana key, webapp JWT signing key, any future credentials) live in the **macOS Keychain** under the service name `Interceder`.
- Access is via the Python `keyring` library backed by the macOS Keychain.
- `config.toml` references secrets by their Keychain entry name only — never the value.
- Secrets are never logged. A redactor runs on all outbound logs that pattern-matches known-secret shapes.
- The Gateway never has access to any secret it doesn't need (e.g. it has Slack tokens but not the Veo key).

### Network exposure
- **Inbound:** zero public ports. The only inbound traffic is on the Tailscale network.
- **Outbound:** Slack Socket Mode (outbound websocket to `slack.com`), Claude Agent SDK (outbound to Anthropic), Veo/Nano Banana (outbound to Google), MCP servers (as installed), explicit user-directed URL fetches.
- No UPnP, no port forwarding, no cloud relay. A single `tailscaled` is the only listening daemon on non-loopback.
- Gateway's FastAPI server binds to the Tailscale interface address explicitly, not `0.0.0.0`.

### Behavioral / persona rules (baked into the Manager's core prompt)
- **Never forget** — memory search is mandatory before any answer that could reference prior context.
- **Never be sycophantic** — disagreement is expected when warranted; no empty agreement or hedging.
- These are enforced by a self-check skill run at the start of every turn, AND by prompt-level discipline, AND by a weekly reflection that scores the Manager's own recent behavior and writes corrections into hot memory if it notices drift.

---

## Karpathy loop integration

All three layers (L1, L2, L3) are implemented as specializations of a single `KarpathyLoop` core.

### Core primitive

```python
@dataclass
class LoopConfig:
    layer: Literal["L1", "L2", "L3"]
    editable_asset: Path           # single file the loop is allowed to edit
    metric: Callable[[Path], float]  # takes the candidate state, returns a scalar
    higher_is_better: bool = True
    time_budget: timedelta         # wall-clock ceiling
    cost_budget_usd: Decimal | None  # only applies to paid tools
    iteration_timeout: timedelta   # per-iteration wall clock ceiling
    keep_threshold: float = 0.0    # minimum improvement over best to keep
    branch_name: str               # git branch for commits
    worktree: Path | None          # optional isolated worktree (required for L3)

class KarpathyLoop:
    def __init__(self, config: LoopConfig, memory: Memory, supervisor: Supervisor): ...
    def run(self) -> LoopResult: ...
    def iterate_once(self) -> Iteration: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def abort(self, reason: str) -> None: ...
```

Each iteration:
1. Reads the current editable asset + the loop's history (last N iterations for context).
2. Asks a Worker (fresh SDK session, cheap model for most loops) to produce a candidate edit with rationale.
3. Applies the edit to the asset in the loop's branch.
4. Runs `metric(asset)` inside the worktree with `iteration_timeout` wall clock.
5. If score improves over `best_score` by ≥ `keep_threshold`, commits to the branch with the rationale and updates `best_score`. Else reverts.
6. Writes a `karpathy_iterations` row regardless of kept/discarded.
7. Emits a loop event to the Supervisor which updates the webapp dashboard.

### L2 — skills loop (enabled from day one)

**Editable asset:** any single skill file in `claude-config/skills/` (selected per iteration by the Manager's reflection).
**Metric:** rolling self-graded task success for tasks that invoked that skill, measured over a window of recent invocations.
**Iteration trigger:** runs continuously but *lazily* — triggered by the `task_reflection` post-task hook. A task that invoked skills A and B may add a self-grade event; when enough self-grades accumulate for a skill, a loop iteration is scheduled.
**Worker:** Manager self-grades inline; the edit-candidate generation step uses a Sonnet Worker.
**Keep criterion:** improved success rate over the previous version's rolling window, OR a reflection consensus that the new version is strictly better on interpretive grounds (useful when the sample size is small).
**Rollback:** if a newly-kept skill drops success rate over its next N invocations, auto-revert and log the mis-improvement.

The "writing-skills" meta-skill that Claude Code ships with handles the creation mechanics. L2 is primarily the **metric-tracking + reflection-scheduling scaffolding** — not a reimplementation of skill-editing.

### L3 — project loop (user-activated per project)

**Editable asset:** user-specified file in a user-specified repo. Enforced as a *single* file per loop (Karpathy principle). If the user wants to evolve multiple files, start multiple loops.
**Metric:** user-provided — can be a shell command that prints a number, a Python callable, or a named metric registered in the tool registry. Returns a float.
**Iteration trigger:** continuous until budget exhaust or user pause.
**Worker:** dedicated loop-mode Worker subprocess with reduced tool scope (no `self_modify`, no `schedule_task`, can't spawn more Workers). Its sandbox is an isolated git worktree so the loop's branch history is clean.
**Keep criterion:** strict improvement (user-configurable threshold).
**Safety:** the editable-asset file is the only file the loop can edit. All other files in the worktree are read-only via filesystem-level enforcement. Prevents runaway scope.
**Resume:** if the loop Worker crashes or is killed, the Supervisor can resume it from the last committed iteration without losing history.
**Reporting:** progress stream to the webapp dashboard (live chart of metric vs. iteration, diff list of recent experiments, best-so-far snippet). Morning digest summarizes overnight runs.

### L1 — user-model / prompt loop (user-activated, session-scoped)

**Editable asset:** the Manager's prompt assembly code (e.g. `interceder/manager/prompt_assembler.py`). This is production code, so L1 is locked behind an explicit session-scoped approval — you say "run L1 tonight" and the Manager opens a dedicated branch.
**Metric:** self-graded user-satisfaction, extracted from follow-up messages over a sliding window. A "satisfaction signal" is a lightweight classifier (Haiku) looking at user responses to recent Manager turns: did they thank, redirect, correct, abandon, or ignore?
**Iteration trigger:** batched — L1 runs once per session with N accumulated turns of satisfaction data, not per-turn.
**Worker:** Opus, because editing the prompt-assembler requires deep understanding.
**Keep criterion:** aggregate satisfaction score on a holdout set of held-back turns replayed against the candidate prompt assembler. (Replay uses a small eval harness that runs the candidate's prompt on recorded user messages and scores responses via Haiku self-grader.)
**Safety:** edits to `prompt_assembler.py` require a full Manager restart to take effect. The Supervisor stages the restart, asks for explicit user confirmation, and rolls back on the next turn if the user signals dissatisfaction.
**Rollback:** one command reverts to the last known-good version.

### Shared infrastructure across all three

- **Single `KarpathyLoop` core** lives in `interceder/loops/core.py`. L1/L2/L3 are thin subclasses supplying the metric callable, editable-asset policy, and worker-type.
- **All iterations are git commits.** The loop's history is literally a git log, making the evolution auditable and rollback a one-command operation.
- **Kill switch** pauses all loops. On resume, each loop continues from its last committed state.
- **Budget enforcement** is checked before every iteration; exceeding wall clock or cost budget triggers a graceful stop with a summary.
- **Dashboard integration** — every loop has a live card on the webapp with metric-over-iterations chart, kept/discarded ratio, best score, and pause/resume/abort controls.

---

## Error handling & reliability

### Failure domains and responses

| Failure | Blast radius | Response |
|---|---|---|
| Gateway process crashes | Slack/webapp disconnect briefly | `launchd` restarts immediately. Slack Socket Mode reconnects automatically. Webapp clients auto-reconnect their WebSocket. Inbox queue is WAL-durable, nothing lost. |
| Manager Supervisor crashes mid-turn | One in-flight reply may be truncated | `launchd` restarts. On startup, Manager reads `in_flight` inbox rows and replays them (idempotency key on the `messages` table prevents double-writes). User sees a brief pause, no lost messages. |
| Agent SDK session itself crashes | Same as Manager crash | Supervisor catches the SDK exception, creates a fresh session, rehydrates hot memory from `hot_memory` table, and retries the current turn. |
| Worker subprocess crashes | Only that task's progress | Supervisor sees non-zero exit code and a "died" status event. Decides: retry, report failure to Manager, or escalate to user. Worker's partial transcript is saved regardless. |
| Rate limit hit on Manager session | Manager can't take turns temporarily | Exponential backoff with jitter, starting at 30s, max 10m. User is notified via proactive ping (subject to quiet hours). Inbox queue accumulates. |
| Rate limit hit on a Worker session | That worker stalls | Worker waits with its own backoff. If the wait exceeds the worker's time budget, it reports stall to Manager who decides whether to abandon or wait. |
| `memory.sqlite` corruption | Catastrophic | WAL mode + regular integrity checks. On detect, Supervisor refuses to start and emits a recovery proactive message. Daily in-app backup (not Time Machine) to `blobs/snapshots/memory-YYYY-MM-DD.sqlite` keeps last 30 days. |
| Disk full | Writes fail | Memory writes and worker file writes fail loudly. Supervisor enters read-only mode and notifies user. Gateway still accepts messages (inbox write is small) but Manager replies are queued. |
| Tailscale down | Webapp unreachable | Slack still works (Socket Mode is independent). User sees Slack-only experience until Tailscale is back. |
| Slack connectivity lost | Slack silent | Webapp still works. Gateway retries Slack Socket Mode connection with backoff. Proactive messages accumulate in `outbox` and deliver on reconnect. |
| Claude subscription expires or is revoked | Manager has no compute | Supervisor detects auth failure, enters a "no compute" mode: acknowledges user messages via the Gateway with a canned "subscription issue, please check" reply, no Manager reasoning, no Worker spawns. |
| Third-party API (Veo/Nano Banana) down | Those tools fail | Tool wrapper catches, returns structured error to Manager, Manager decides whether to retry, fall back, or report. |

### Queue delivery semantics
- Both `inbox` and `outbox` are **at-least-once**. Every message carries an idempotency key.
- The `messages` table has a UNIQUE constraint on `id`; attempting to re-insert an already-processed message is a no-op.
- On Supervisor startup, it scans for rows where `status='in_flight'` and either retries them (if not yet appended to `messages`) or marks them complete (if already processed).
- On Gateway startup, it scans `outbox` for undelivered rows and replays them to Slack/webapp.

### Crash recovery of the Manager's working state
The Manager's state is not in memory — it's in the SQLite archive. On restart:
1. Rehydrate hot memory from `hot_memory` table.
2. Load the last N messages from the current `correlation_id` into the Agent SDK session as prior turns.
3. Reconcile active workers (status = "running" but PID not alive → mark as "crashed" and ask Manager what to do).
4. Reconcile active Karpathy loops (same pattern).
5. Announce via a proactive "I'm back" message if the downtime exceeded a threshold (configurable, default 5 minutes).

### Backup strategy
- **Primary:** Time Machine covers `~/Library/Application Support/Interceder/` automatically if the user has it enabled.
- **Secondary (always on):** a daily in-app backup job writes a snapshot of `memory.sqlite` (using `sqlite3 .backup` for consistency) to `blobs/snapshots/`. Keeps the last 30 days; older snapshots are pruned.
- **Tertiary (user-invoked):** `/backup <dest>` command archives the whole Interceder directory to a user-specified path (e.g. external drive, encrypted volume).

---

## Testing strategy

### Test taxonomy

**Unit tests (pytest)**
- Memory layer: schema migrations, FTS5 indexing, hot/cold promote/demote, tombstone semantics, entity extraction.
- Approval system: all three tiers, the `PreToolUse` hook response shape, AFK grant scope matching, expiration.
- Scheduler: cron parsing, `tick()` logic, scope-to-message synthesis.
- Message schema: roundtrip through Slack renderer, webapp renderer, canonical form.
- Tool wrappers: each custom tool's input/output validation and error paths.
- Karpathy loop core: keep/discard logic with synthetic metrics, git branch bookkeeping, budget enforcement.

**Integration tests**
- Gateway↔Manager via the SQLite queue: end-to-end inbound→reply without hitting Claude (use a stub Agent SDK session that returns scripted responses).
- Slack Socket Mode event handling: replay recorded Slack events through the Gateway, assert the outbox shape.
- Webapp WebSocket: synthetic clients connect, send messages, receive broadcasts, reconcile read state.
- Worker subprocess lifecycle: spawn, stream events, complete, transcript-fold.
- Self-modification: propose an edit, observe the git commit, verify restart scheduling, verify rollback.

**End-to-end tests (scripted scenarios)**
- Each of the five canonical data-flow scenarios (A–E) is a named e2e test using a stubbed Agent SDK that returns scripted responses matching the scenario.
- A tests-only "Claude stub" implements the Agent SDK interface with deterministic canned behaviors.

**Security tests**
- For each Tier-2 action, assert both the `PreToolUse` hook AND the runtime wrapper deny it, independently.
- Fuzz the message schema and approval context with malformed inputs; assert no crashes, no unexpected allows.
- Attempt to have a Worker write outside its sandbox; assert it's blocked at filesystem layer.
- Attempt to have `self_modify` touch a protected file; assert double-layer block.

**Chaos tests**
- Kill the Manager process mid-worker; assert recovery on restart (worker state reconciled, transcript preserved).
- Kill a worker mid-task; assert Manager notices and reports.
- Simulate rate-limit exhaustion; assert backoff and user notification.
- Corrupt a single row in `messages`; assert the fault doesn't cascade.

**Load tests (rough)**
- 50 queued inbound messages processed in order; all eventually replied.
- 10 concurrent workers; no deadlocks in the memory layer.
- 1000-message chat history in the webapp; scroll performance acceptable.

### Test data
- Fixture: a synthetic memory archive with ~500 messages, ~50 workers, ~10 loops, ~100 facts, used for memory-layer and webapp tests.
- Fixture: a recorded set of Slack Socket Mode events for integration tests.
- Fixture: a scripted Agent SDK stub for deterministic Manager-turn tests.

### CI
- Runs on push: unit + integration + security tests.
- Runs on PR: all of the above + end-to-end scripted scenarios + chaos tests.
- Load tests run nightly on the dev Mac, not CI.

---

## Deployment, first-run, and updates

### Project layout

```
interceder/
├── pyproject.toml              # uv-managed
├── README.md
├── plan.md
├── src/
│   └── interceder/
│       ├── gateway/            # Gateway service package
│       ├── manager/            # Manager Supervisor service package
│       ├── worker/             # Worker entrypoint + stdlib
│       ├── memory/             # Memory layer (library)
│       ├── approval/           # Approval + audit (library)
│       ├── scheduler/          # Scheduler (library)
│       ├── loops/              # KarpathyLoop core + L1/L2/L3 subclasses
│       ├── tools/              # custom tool implementations
│       ├── webapp/             # (React or SolidStart source; build emits static dist)
│       ├── migrations/         # forward-only SQL migrations
│       ├── config.py           # model IDs, tier definitions, defaults
│       └── __main__.py
├── deploy/
│   ├── com.interceder.gateway.plist
│   ├── com.interceder.manager.plist
│   └── install.sh              # first-run setup script
└── tests/
    └── ...
```

### launchd services

Two plists, both `RunAtLoad=true`, `KeepAlive=true`:
- `com.interceder.gateway` — starts the Gateway, sets env for `INTERCEDER_HOME`, binds FastAPI to the Tailscale interface.
- `com.interceder.manager` — starts the Manager Supervisor, depends on the Gateway being started first (polls a health endpoint with backoff).

Both log stdout/stderr to `~/Library/Application Support/Interceder/logs/gateway.log` and `manager.log` with daily rotation.

### First-run setup script (`install.sh`)
1. Verify prerequisites: macOS, Python ≥3.12, Tailscale running, Claude Code CLI logged in with Max subscription, git.
2. Create the `~/Library/Application Support/Interceder/` directory tree.
3. Initialize `memory.sqlite` by running all migrations forward.
4. Create the Interceder Claude config (`claude-config/`) with a starter `settings.json`, an empty `skills/` git repo, and any MCP servers the user wants.
5. Interactive prompts for Keychain entries:
   - Slack app token (xoxb-...) and bot token (xapp-...) for Socket Mode.
   - Webapp JWT signing key (auto-generated and stored).
   - Veo API key (optional, can add later).
   - Nano Banana / Gemini API key (optional, can add later).
6. Write a starter `config.toml` (allowlist empty, quiet hours defaulted to 11pm–7am, proactive rate-limits set).
7. Install both launchd plists to `~/Library/LaunchAgents/` and `launchctl load` them.
8. Open the webapp URL in the default browser.

### Updates
- `git pull` in the install directory.
- Run `interceder migrate` to apply any new SQL migrations (forward-only, transactional).
- `launchctl kickstart -k gui/$UID/com.interceder.manager` — restarts the Manager with the new code. Gateway can be updated independently.
- Schema migrations are tested by CI against a fixture archive.
- Rollback: checkout previous commit, `launchctl kickstart` again. Schema migrations are forward-only; rollbacks of schema are manual.

### Phased build order

This is an ambitious spec. To avoid a big-bang build, the implementation plan will proceed in phases. Each phase ships something demo-able.

**Phase 0 — Skeleton**
Project structure, pyproject, launchd plists, Claude config scaffolding, empty Gateway and Manager services, first-run install script basics. Outcome: both services start, do nothing useful, exit cleanly.

**Phase 1 — Gateway talks to Slack**
Gateway wires up Slack Socket Mode, receives DMs, writes to `inbox`. Webapp is not yet built; Gateway serves a placeholder page. Outcome: you can send a Slack message to Interceder and see it show up in `inbox`.

**Phase 2 — Manager echoes**
Manager Supervisor drains `inbox`, starts a minimal Agent SDK session (no custom tools yet), gets a reply, writes to `outbox`. Gateway sends the reply back. Outcome: you can chat with a trivial Opus on Slack; no memory yet.

**Phase 3 — Memory layer + recall**
SQLite schema migrations, the `Memory` Python interface, `memory_recall` / `memory_write` custom tools, hot memory table + injection, "never forget" system prompt and self-check skill. Outcome: Manager remembers and searches past conversations. Passes the "what did we figure out about caching" test.

**Phase 4 — Workers (out-of-process)**
`spawn_worker_process` custom tool, Worker stdlib (stdout JSONL, sandbox dir, scoped tools), Supervisor lifecycle management, worker status streaming to the Manager. Outcome: Manager can hand off multi-step work to Workers and see them complete.

**Phase 5 — Approval system**
`Approval.check`, Tier-0/1/2 enforcement via `PreToolUse` hook + runtime wrappers, approval queue persistence, proactive approval messages over Slack. Outcome: Tier-1 actions gate correctly on reactji.

**Phase 6 — Webapp MVP (chat pane)**
Static SPA built, served by Gateway, WebSocket connected, chat pane at parity with Slack. Mobile-responsive from day one. Outcome: you can chat with the Manager from a browser over Tailscale.

**Phase 7 — Karpathy L2 skills loop**
Skill library git repo, post-task `task_reflection` skill hook, self-grading, skill edit-and-keep logic, rollback on regression. Outcome: Manager refines its own skills over time.

**Phase 8 — Dashboard panes**
Build the remaining webapp panes in order: **workers → approvals → memory browser → schedules → settings**. Each pane is a shipping milestone.

**Phase 9 — Scheduler + proactive behaviors**
Scheduler, all eight proactive-message classes, quiet hours, digest, rate limiting. Outcome: Manager speaks first in all the right ways.

**Phase 10 — MCP and third-party integrations**
Investigate and install any useful MCP servers (GitHub, filesystem, Google GenAI). Fill gaps with custom tools (Veo, Nano Banana). Cost tracking table + dashboard card. Outcome: Manager can generate media and has rich tool reach.

**Phase 11 — Karpathy L3 project loops**
KarpathyLoop core, L3 subclass, worktree management, metric callable registry, webapp loop-dashboard pane, user-facing `start_karpathy_loop` flow. Outcome: user can run an overnight loop on a real repo.

**Phase 12 — Karpathy L1 user-model loop (opt-in)**
L1 subclass, prompt-assembler refactor to be editable, satisfaction classifier, holdout eval harness, restart-on-accept flow, rollback. Outcome: Manager can evolve its own user-understanding prompt across sessions.

**Phase 13 — AFK mode, kill switches, polish**
AFK grant tool, scope matching, all kill switches, audit log browser, final security audit, documentation. Outcome: v1 complete.

Phases 0–6 get you a working remote Claude with persistent memory. Phases 7–13 add the self-improvement and richer UX.

---

## Out of scope (YAGNI)

Explicitly deferred to future versions or forever:

- **Voice input/output.** No STT, no TTS, no audio transcription, no voice replies — in either direction.
- **In-browser code editor / diff viewer.** The webapp links out to the user's editor and GitHub instead of embedding a Monaco/CodeMirror pane.
- **Multi-tenant / hosted product.** The architecture leaves a single clean seam for a second user (the user's wife), and nothing more.
- **Billing, quotas, rate limits per user.** Single-user, Max subscription.
- **Public internet exposure.** No Tailscale Funnel in v1, no public webapp URL, no public Gateway endpoint. All access via tailnet + Slack Socket Mode.
- **Mobile native apps.** The responsive webapp serves mobile use.
- **Federated or cross-machine Manager.** Manager lives on one Mac. If the Mac dies, recover from Time Machine; don't build cross-host replication.
- **Email or SMS notifications.** No integrations with email, iMessage, SMS, push notification services. Slack DM + webapp is the delivery surface.
- **Payments / financial transactions.** Hard blocked — no Stripe/Plaid/banking APIs.
- **Docker / containerization.** Runs as native macOS processes under launchd. No Docker Desktop dependency.
- **Cross-platform support.** macOS only. Linux/Windows are not supported.
- **Arbitrary MCP server auto-install.** MCP servers are added manually by the user; the Manager is not permitted to install new MCP servers on its own (Tier 1 at best, and deferred).
- **Visual diff of Karpathy iteration changes.** Webapp shows the diff as text; no rendered visual comparisons.
- **Fine-tuned memory-embedding search.** v1 uses SQLite FTS5 + the Hindsight-style structured layer. Vector search can be added later behind the `Memory.recall` interface without API changes.
- **Hot-patching Manager code.** Self-edits to Manager Python require a full process restart. No hot-reload trickery.
- **Rich analytics / usage reports beyond cost and approvals.** The webapp dashboard is operational, not analytical. No "insights" pane, no monthly reports, no graphs beyond Karpathy loops.
- **Team / collaborative features.** No mentions, no per-channel scoping beyond the single user's DM, no group conversations.
