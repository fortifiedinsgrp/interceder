-- 0001_init.sql — bootstrap the Interceder memory database.
--
-- Phase 0 scope: the two durable queue tables that bridge the Gateway and
-- the Manager Supervisor. The full memory archive (messages/FTS5, entities,
-- facts, reflections, workers, approvals, schedules, loops, costs) arrives
-- in later phases as additional migration files (0002 onward).

-- Inbox: Gateway writes here; Manager Supervisor drains it.
CREATE TABLE inbox (
    id              TEXT PRIMARY KEY,                -- UUID, idempotency key
    correlation_id  TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT 'me',
    source          TEXT NOT NULL,                   -- slack|webapp|scheduler:*|...
    kind            TEXT NOT NULL,                   -- text|attachment|approval_resolution|...
    content         TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'queued',  -- queued|in_flight|completed|failed
    in_flight_pid   INTEGER,
    created_at      INTEGER NOT NULL,
    processed_at    INTEGER
);
CREATE INDEX idx_inbox_status_created ON inbox(status, created_at);
CREATE INDEX idx_inbox_correlation   ON inbox(correlation_id);

-- Outbox: Manager writes here; Gateway drains it to Slack and webapp.
CREATE TABLE outbox (
    id              TEXT PRIMARY KEY,
    correlation_id  TEXT NOT NULL,
    inbox_id        TEXT,                            -- nullable: proactives have no inbox origin
    source          TEXT NOT NULL,                   -- manager|manager_proactive|worker_event|approval
    kind            TEXT NOT NULL,                   -- text|tool_result|approval_request|worker_update|proactive
    content         TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'queued',  -- queued|in_flight|delivered|failed
    delivered_slack INTEGER NOT NULL DEFAULT 0,
    delivered_web   INTEGER NOT NULL DEFAULT 0,
    created_at      INTEGER NOT NULL,
    delivered_at    INTEGER
);
CREATE INDEX idx_outbox_status_created ON outbox(status, created_at);
CREATE INDEX idx_outbox_correlation   ON outbox(correlation_id);
