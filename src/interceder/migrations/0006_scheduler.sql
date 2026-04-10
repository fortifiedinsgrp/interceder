-- 0006_scheduler.sql — Scheduled tasks + cost tracking.

CREATE TABLE schedules (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    cron_expr       TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    scope_json      TEXT NOT NULL DEFAULT '{}',
    enabled         INTEGER NOT NULL DEFAULT 1,
    last_run_at     INTEGER,
    next_run_at     INTEGER NOT NULL,
    created_at      INTEGER NOT NULL
);

CREATE TABLE costs (
    id              INTEGER PRIMARY KEY,
    tool            TEXT NOT NULL,
    key_name        TEXT NOT NULL,
    workflow_id     TEXT,
    usd_cents       INTEGER NOT NULL,
    units_json      TEXT NOT NULL DEFAULT '{}',
    created_at      INTEGER NOT NULL
);
CREATE INDEX idx_costs_tool ON costs(tool, created_at);
