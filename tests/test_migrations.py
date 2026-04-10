"""Tests for the forward-only SQL migration runner."""
from __future__ import annotations

from pathlib import Path

import pytest

from interceder.memory import db, runner


def _write_migration(migrations_dir: Path, name: str, sql: str) -> Path:
    path = migrations_dir / name
    path.write_text(sql)
    return path


def test_migrate_applies_first_migration(tmp_path: Path) -> None:
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    _write_migration(mig_dir, "0001_init.sql", "CREATE TABLE foo (id INTEGER);")

    db_file = tmp_path / "memory.sqlite"
    version = runner.migrate(db_path=db_file, migrations_dir=mig_dir)

    assert version == 1
    conn = db.connect(db_file)
    try:
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "schema_meta" in tables
        assert "foo" in tables
    finally:
        conn.close()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    _write_migration(mig_dir, "0001_init.sql", "CREATE TABLE foo (id INTEGER);")

    db_file = tmp_path / "memory.sqlite"
    runner.migrate(db_path=db_file, migrations_dir=mig_dir)
    runner.migrate(db_path=db_file, migrations_dir=mig_dir)  # second pass = no-op

    conn = db.connect(db_file)
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM schema_meta").fetchone()["c"]
        assert count == 1
    finally:
        conn.close()


def test_migrate_applies_multiple_in_order(tmp_path: Path) -> None:
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    _write_migration(mig_dir, "0001_init.sql", "CREATE TABLE a (id INTEGER);")
    _write_migration(mig_dir, "0002_add_b.sql", "CREATE TABLE b (id INTEGER);")
    _write_migration(mig_dir, "0003_add_c.sql", "CREATE TABLE c (id INTEGER);")

    db_file = tmp_path / "memory.sqlite"
    version = runner.migrate(db_path=db_file, migrations_dir=mig_dir)
    assert version == 3

    conn = db.connect(db_file)
    try:
        for t in ("a", "b", "c"):
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (t,),
            ).fetchone()
            assert row is not None, f"missing table {t}"
    finally:
        conn.close()


def test_migrate_rejects_sequence_gap(tmp_path: Path) -> None:
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    _write_migration(mig_dir, "0001_init.sql", "CREATE TABLE a (id INTEGER);")
    _write_migration(mig_dir, "0003_gap.sql", "CREATE TABLE c (id INTEGER);")

    db_file = tmp_path / "memory.sqlite"
    with pytest.raises(runner.MigrationError, match="gap|0002"):
        runner.migrate(db_path=db_file, migrations_dir=mig_dir)


def test_migrate_ignores_non_migration_files(tmp_path: Path) -> None:
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    _write_migration(mig_dir, "0001_init.sql", "CREATE TABLE a (id INTEGER);")
    (mig_dir / "README.md").write_text("not a migration")
    (mig_dir / "__init__.py").write_text("")

    db_file = tmp_path / "memory.sqlite"
    version = runner.migrate(db_path=db_file, migrations_dir=mig_dir)
    assert version == 1


def test_migrate_rolls_back_failed_migration(tmp_path: Path) -> None:
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    _write_migration(mig_dir, "0001_init.sql", "CREATE TABLE a (id INTEGER);")
    _write_migration(
        mig_dir,
        "0002_broken.sql",
        "CREATE TABLE b (id INTEGER); THIS_IS_NOT_SQL;",
    )

    db_file = tmp_path / "memory.sqlite"
    with pytest.raises(runner.MigrationError):
        runner.migrate(db_path=db_file, migrations_dir=mig_dir)

    conn = db.connect(db_file)
    try:
        version = conn.execute(
            "SELECT MAX(version) AS v FROM schema_meta"
        ).fetchone()["v"]
        assert version == 1  # 0002 rolled back
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='b'"
        ).fetchone()
        assert row is None
    finally:
        conn.close()
