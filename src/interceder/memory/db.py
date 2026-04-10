"""SQLite connection helper — WAL, foreign keys, Row factory."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    """Open (creating if needed) a SQLite DB with standard Interceder defaults.

    - Parent directory is created if missing.
    - journal_mode=WAL for durability + concurrent reads (N1).
    - foreign_keys=ON for referential integrity.
    - synchronous=NORMAL (WAL-safe; balances durability and throughput).
    - row_factory=sqlite3.Row for dict-like column access.
    - isolation_level=None: autocommit mode; callers manage transactions
      explicitly via BEGIN / COMMIT / ROLLBACK.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn
