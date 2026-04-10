-- 0003_workers.sql — Worker tracking tables.

CREATE TABLE workers (
    id              TEXT PRIMARY KEY,
    parent_id       TEXT,
    task_spec_json  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',
    model           TEXT NOT NULL,
    sandbox_dir     TEXT NOT NULL,
    pid             INTEGER,
    started_at      INTEGER,
    ended_at        INTEGER,
    summary         TEXT,
    transcript_path TEXT
);

CREATE TABLE worker_events (
    id              INTEGER PRIMARY KEY,
    worker_id       TEXT NOT NULL REFERENCES workers(id),
    event_kind      TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    created_at      INTEGER NOT NULL
);
CREATE INDEX idx_worker_events_worker ON worker_events(worker_id, created_at);
