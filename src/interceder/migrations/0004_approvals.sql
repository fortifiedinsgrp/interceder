-- 0004_approvals.sql — Approval queue, AFK grants, audit log.

CREATE TABLE approvals (
    id              TEXT PRIMARY KEY,
    action          TEXT NOT NULL,
    context_json    TEXT NOT NULL,
    tier            INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    requested_by    TEXT NOT NULL,
    resolved_by     TEXT,
    resolved_at     INTEGER,
    expires_at      INTEGER NOT NULL,
    created_at      INTEGER NOT NULL
);
CREATE INDEX idx_approvals_status ON approvals(status);

CREATE TABLE afk_grants (
    id              TEXT PRIMARY KEY,
    scope_json      TEXT NOT NULL,
    granted_at      INTEGER NOT NULL,
    expires_at      INTEGER NOT NULL,
    revoked_at      INTEGER
);

CREATE TABLE audit_log (
    id              INTEGER PRIMARY KEY,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    tier            INTEGER NOT NULL,
    outcome         TEXT NOT NULL,
    context_json    TEXT NOT NULL,
    created_at      INTEGER NOT NULL
);
CREATE INDEX idx_audit_created ON audit_log(created_at);
