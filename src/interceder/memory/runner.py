"""Forward-only SQL migration runner.

Scans a migrations directory for files named `NNNN_<slug>.sql`, applies
any with a version higher than the current `schema_meta` max version,
in ascending order. Each migration runs inside an explicit transaction;
any failure rolls back and raises MigrationError, leaving the DB at the
previous consistent version.
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

from interceder import config
from interceder.memory import db as db_module


class MigrationError(RuntimeError):
    """Raised when the migrator detects a bad state or a migration fails."""


_MIGRATION_FILENAME = re.compile(r"^(\d{4})_[A-Za-z0-9_\-]+\.sql$")


def _discover(migrations_dir: Path) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    for entry in sorted(migrations_dir.iterdir()):
        if not entry.is_file():
            continue
        match = _MIGRATION_FILENAME.match(entry.name)
        if not match:
            continue
        found.append((int(match.group(1)), entry))
    found.sort(key=lambda t: t[0])
    return found


def _ensure_schema_meta(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            version    INTEGER PRIMARY KEY,
            applied_at INTEGER NOT NULL
        )
        """
    )


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(version) AS v FROM schema_meta").fetchone()
    return row["v"] or 0


def _validate_sequence(
    migrations: list[tuple[int, Path]], current: int
) -> list[tuple[int, Path]]:
    pending = [(v, p) for (v, p) in migrations if v > current]
    expected = current + 1
    for version, path in pending:
        if version != expected:
            raise MigrationError(
                f"migration sequence gap: expected {expected:04d}, "
                f"found {version:04d} at {path.name}"
            )
        expected += 1
    return pending


def _apply(conn: sqlite3.Connection, version: int, path: Path) -> None:
    sql = path.read_text()
    ts = int(time.time())
    # executescript() implicitly COMMITs any open transaction before running,
    # so we must bundle BEGIN + migration + bookkeeping + COMMIT into one
    # script to get atomic all-or-nothing semantics.
    full_script = (
        f"BEGIN;\n"
        f"{sql}\n"
        f"INSERT INTO schema_meta (version, applied_at) VALUES ({version}, {ts});\n"
        f"COMMIT;\n"
    )
    try:
        conn.executescript(full_script)
    except Exception as exc:  # noqa: BLE001 — re-raise as MigrationError
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise MigrationError(f"migration {path.name} failed: {exc}") from exc


def migrate(
    db_path: Path | None = None,
    migrations_dir: Path | None = None,
    *,
    db_path_override: str | None = None,
) -> int:
    """Apply all pending migrations. Returns the resulting schema version.

    Defaults read from `interceder.config` so production callers (install.sh,
    `interceder migrate`) pass nothing. Tests pass explicit paths.
    """
    if db_path_override is not None:
        db_path = Path(db_path_override)
    if db_path is None:
        db_path = config.db_path()
    if migrations_dir is None:
        migrations_dir = config.migrations_dir()

    conn = db_module.connect(db_path)
    try:
        _ensure_schema_meta(conn)
        current = _current_version(conn)
        pending = _validate_sequence(_discover(migrations_dir), current)
        for version, path in pending:
            _apply(conn, version, path)
        return _current_version(conn)
    finally:
        conn.close()
