"""Integration test: 0002 memory archive migration applies cleanly."""
from __future__ import annotations

from pathlib import Path

from interceder import config
from interceder.memory import db, runner


def test_0002_creates_memory_tables(tmp_interceder_home: Path) -> None:
    db_file = tmp_interceder_home / "db" / "memory.sqlite"
    runner.migrate(db_path=db_file, migrations_dir=config.migrations_dir())

    conn = db.connect(db_file)
    try:
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "messages", "blobs", "attachments", "entities", "facts",
            "relationships", "reflections", "hot_memory",
        }
        assert expected.issubset(tables), f"missing: {expected - tables}"

        # Verify FTS5 virtual table
        vtables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'"
            ).fetchall()
        }
        assert "messages_fts" in vtables
    finally:
        conn.close()


def test_messages_insert_triggers_fts(tmp_interceder_home: Path) -> None:
    db_file = tmp_interceder_home / "db" / "memory.sqlite"
    runner.migrate(db_path=db_file, migrations_dir=config.migrations_dir())

    conn = db.connect(db_file)
    try:
        conn.execute(
            """
            INSERT INTO messages (id, correlation_id, user_id, source, kind, role, content, metadata_json, created_at)
            VALUES ('m1', 'c1', 'me', 'slack', 'text', 'user', 'hello world search test', '{}', 1700000000)
            """
        )
        results = conn.execute(
            "SELECT * FROM messages_fts WHERE messages_fts MATCH 'search'",
        ).fetchall()
        assert len(results) == 1
    finally:
        conn.close()
