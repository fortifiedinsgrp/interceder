"""Tests for interceder.memory.db — WAL-mode SQLite connection helper."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from interceder.memory import db


def test_connect_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "dir" / "memory.sqlite"
    conn = db.connect(target)
    try:
        assert target.parent.is_dir()
        assert target.exists()
    finally:
        conn.close()


def test_connect_enables_wal_mode(tmp_path: Path) -> None:
    target = tmp_path / "memory.sqlite"
    conn = db.connect(target)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()


def test_connect_enables_foreign_keys(tmp_path: Path) -> None:
    target = tmp_path / "memory.sqlite"
    conn = db.connect(target)
    try:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
    finally:
        conn.close()


def test_connect_returns_row_factory(tmp_path: Path) -> None:
    target = tmp_path / "memory.sqlite"
    conn = db.connect(target)
    try:
        assert conn.row_factory is sqlite3.Row
    finally:
        conn.close()
