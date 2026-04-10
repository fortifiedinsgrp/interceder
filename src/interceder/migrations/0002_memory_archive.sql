-- 0002_memory_archive.sql — Full memory archive tables.
--
-- Core message log, FTS5 search, blob storage, structured long-term
-- layer (entities, facts, relationships, reflections), and hot memory.

-- Core message log — the spine of everything
CREATE TABLE messages (
    id              TEXT PRIMARY KEY,
    correlation_id  TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT 'me',
    source          TEXT NOT NULL,
    kind            TEXT NOT NULL,
    role            TEXT NOT NULL,     -- user|assistant|tool|system
    content         TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    tombstoned_at   INTEGER,
    created_at      INTEGER NOT NULL
);
CREATE INDEX idx_messages_correlation ON messages(correlation_id, created_at);
CREATE INDEX idx_messages_created ON messages(created_at);

-- Full-text search over message content
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content, source, kind, content='messages', content_rowid='rowid'
);

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

-- Content-addressed blob metadata
CREATE TABLE blobs (
    sha256          TEXT PRIMARY KEY,
    byte_size       INTEGER NOT NULL,
    mime_type       TEXT NOT NULL,
    origin          TEXT NOT NULL,
    created_at      INTEGER NOT NULL
);

-- Attachments link messages to blobs
CREATE TABLE attachments (
    message_id      TEXT NOT NULL REFERENCES messages(id),
    sha256          TEXT NOT NULL REFERENCES blobs(sha256),
    label           TEXT,
    PRIMARY KEY (message_id, sha256)
);

-- Structured long-term layer
CREATE TABLE entities (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    kind            TEXT NOT NULL,
    properties_json TEXT NOT NULL DEFAULT '{}',
    first_seen_msg  TEXT REFERENCES messages(id),
    last_seen_at    INTEGER NOT NULL
);
CREATE UNIQUE INDEX idx_entities_name_kind ON entities(name, kind);

CREATE TABLE facts (
    id              INTEGER PRIMARY KEY,
    entity_id       INTEGER REFERENCES entities(id),
    claim           TEXT NOT NULL,
    confidence      REAL NOT NULL,
    source_msg_id   TEXT REFERENCES messages(id),
    extracted_at    INTEGER NOT NULL,
    superseded_by   INTEGER REFERENCES facts(id)
);

CREATE TABLE relationships (
    id              INTEGER PRIMARY KEY,
    subject_id      INTEGER NOT NULL REFERENCES entities(id),
    predicate       TEXT NOT NULL,
    object_id       INTEGER NOT NULL REFERENCES entities(id),
    confidence      REAL NOT NULL,
    source_msg_id   TEXT REFERENCES messages(id),
    extracted_at    INTEGER NOT NULL
);

CREATE TABLE reflections (
    id              INTEGER PRIMARY KEY,
    kind            TEXT NOT NULL,
    scope_json      TEXT NOT NULL,
    content         TEXT NOT NULL,
    source_msg_ids  TEXT NOT NULL,
    created_at      INTEGER NOT NULL
);

-- Hot memory: curated pinned items always in the Manager's context
CREATE TABLE hot_memory (
    id              INTEGER PRIMARY KEY,
    slot            TEXT NOT NULL,
    content         TEXT NOT NULL,
    priority        INTEGER NOT NULL,
    token_estimate  INTEGER NOT NULL,
    last_touched_at INTEGER NOT NULL
);
