"""Tests for the Memory archive — recall, write, tombstone, entities."""
from __future__ import annotations

import time
from pathlib import Path

from interceder import config
from interceder.memory import db, runner
from interceder.memory.archive import Memory


def _setup(tmp_interceder_home: Path) -> Memory:
    runner.migrate()
    conn = db.connect(config.db_path())
    return Memory(conn)


def test_write_and_recall(tmp_interceder_home: Path) -> None:
    mem = _setup(tmp_interceder_home)
    try:
        mem.write_message(
            id="m1", correlation_id="c1", role="user", source="slack",
            kind="text", content="I prefer tabs over spaces", created_at=int(time.time()),
        )
        results = mem.recall("tabs spaces")
        assert len(results) >= 1
        assert any("tabs" in r["content"] for r in results)
    finally:
        mem.close()


def test_recall_excludes_tombstoned(tmp_interceder_home: Path) -> None:
    mem = _setup(tmp_interceder_home)
    try:
        mem.write_message(
            id="m-tomb", correlation_id="c1", role="user", source="slack",
            kind="text", content="secret embarrassing thing", created_at=int(time.time()),
        )
        count = mem.tombstone("m-tomb")
        assert count == 1
        results = mem.recall("embarrassing")
        assert len(results) == 0
    finally:
        mem.close()


def test_write_entity_and_fact(tmp_interceder_home: Path) -> None:
    mem = _setup(tmp_interceder_home)
    try:
        eid = mem.add_entity(name="React", kind="tool")
        fid = mem.add_fact(entity_id=eid, claim="preferred frontend framework", confidence=0.9)
        entities = mem.search_entities("React")
        assert len(entities) >= 1
        assert entities[0]["name"] == "React"
    finally:
        mem.close()


def test_hot_memory_promote_demote(tmp_interceder_home: Path) -> None:
    mem = _setup(tmp_interceder_home)
    try:
        hid = mem.promote(slot="pinned_facts", content="user prefers tabs", priority=10, token_estimate=5)
        hot = mem.get_hot_memory()
        assert any("tabs" in h["content"] for h in hot)
        mem.demote(hid)
        hot2 = mem.get_hot_memory()
        assert not any(h["id"] == hid for h in hot2)
    finally:
        mem.close()
