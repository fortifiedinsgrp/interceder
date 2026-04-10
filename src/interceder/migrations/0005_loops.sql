-- 0005_loops.sql — Karpathy loop state tracking.

CREATE TABLE karpathy_loops (
    id                      TEXT PRIMARY KEY,
    layer                   TEXT NOT NULL,
    editable_asset          TEXT NOT NULL,
    metric_name             TEXT NOT NULL,
    metric_definition_json  TEXT NOT NULL,
    branch                  TEXT NOT NULL,
    worktree                TEXT,
    status                  TEXT NOT NULL DEFAULT 'running',
    best_score              REAL,
    iterations              INTEGER NOT NULL DEFAULT 0,
    budget_json             TEXT NOT NULL,
    started_at              INTEGER NOT NULL,
    ended_at                INTEGER
);

CREATE TABLE karpathy_iterations (
    id              INTEGER PRIMARY KEY,
    loop_id         TEXT NOT NULL REFERENCES karpathy_loops(id),
    iteration       INTEGER NOT NULL,
    commit_hash     TEXT NOT NULL,
    metric_value    REAL NOT NULL,
    kept            INTEGER NOT NULL,
    rationale       TEXT NOT NULL,
    wall_seconds    INTEGER NOT NULL,
    created_at      INTEGER NOT NULL
);
CREATE INDEX idx_iterations_loop ON karpathy_iterations(loop_id, iteration);
