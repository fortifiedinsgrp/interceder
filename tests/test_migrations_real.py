"""Integration test: the packaged 0001 migration applies cleanly."""
from __future__ import annotations

from pathlib import Path

from interceder import config
from interceder.memory import db, runner


def test_packaged_migrations_apply(tmp_path: Path) -> None:
    db_file = tmp_path / "memory.sqlite"
    version = runner.migrate(db_path=db_file, migrations_dir=config.migrations_dir())
    assert version >= 1

    conn = db.connect(db_file)
    try:
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"schema_meta", "inbox", "outbox"}.issubset(tables)
    finally:
        conn.close()


def test_inbox_roundtrip_insert(tmp_path: Path) -> None:
    db_file = tmp_path / "memory.sqlite"
    runner.migrate(db_path=db_file, migrations_dir=config.migrations_dir())

    conn = db.connect(db_file)
    try:
        conn.execute(
            """
            INSERT INTO inbox (id, correlation_id, source, kind, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("msg-1", "conv-1", "slack", "text", "hi", 1700000000),
        )
        row = conn.execute(
            "SELECT id, status, user_id FROM inbox WHERE id=?", ("msg-1",)
        ).fetchone()
        assert row["id"] == "msg-1"
        assert row["status"] == "queued"        # default
        assert row["user_id"] == "me"           # default
    finally:
        conn.close()
