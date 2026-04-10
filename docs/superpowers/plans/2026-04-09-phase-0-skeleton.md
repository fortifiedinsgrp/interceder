# Phase 0 — Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up Interceder's two-process skeleton — a Gateway service and a Manager Supervisor service — with `pyproject.toml`, a SQLite migration runner, launchd plist templates, and a first-run `install.sh`. Outcome: both services boot via `python -m interceder`, the Gateway serves `/health`, the Manager Supervisor opens the DB and runs a heartbeat tick loop, and both shut down cleanly on SIGTERM.

**Architecture:** Python 3.12+ `src/`-layout package managed by `uv`. Two independent service entry points (`interceder gateway`, `interceder manager`) dispatched by a single click-based CLI. A forward-only SQL migration runner targets `memory.sqlite` under `~/Library/Application Support/Interceder/`. A `deploy/install.sh` bootstraps the directory tree, runs migrations, seeds an isolated `claude-config/` with an empty `skills/` git repo, and (optionally) installs launchd plists. No Claude Agent SDK, no Slack, no webapp — those arrive in Phases 2, 1, and 6 respectively.

**Tech Stack:** Python 3.12+, uv, FastAPI, uvicorn, click, pydantic, keyring, pytest, pytest-timeout, httpx (test-only), SQLite 3.43+ in WAL mode, macOS launchd, bash.

**Scope note — this plan is Phase 0 only.** `plan.md` describes Phases 0–13 (Skeleton → AFK mode / polish). Subsequent phase plans are drafted after the preceding phase ships, so downstream decisions aren't locked in before we've validated the scaffolding. Phase 0 intentionally omits: Slack wiring, Claude Agent SDK wiring, memory archive tables (`messages`, FTS5, entities, etc.), worker subprocess lifecycle, approval system, webapp, and everything under the self-improvement / proactive umbrellas.

---

## File structure

Each file below has one clear responsibility. Files that change together live together.

**Project root**
- `.gitignore` — ignore Python, uv, test artifacts, and Interceder-local state
- `.python-version` — pin 3.12
- `pyproject.toml` — uv package config and (minimal) dep list

**Source tree (`src/interceder/`)**
- `__init__.py` — package marker
- `__main__.py` — click CLI dispatcher for `gateway`, `manager`, `migrate`
- `config.py` — model IDs, filesystem paths, service defaults (single source of truth for N18)
- `gateway/__init__.py` — package marker
- `gateway/app.py` — FastAPI app factory (health + placeholder root)
- `gateway/service.py` — launchd-managed entry point (uvicorn `Server`)
- `manager/__init__.py` — package marker
- `manager/supervisor.py` — `Supervisor` class skeleton (opens DB, tick stub)
- `manager/service.py` — launchd-managed entry point (tick loop + signal handling)
- `worker/__init__.py` — empty marker (Phase 4 populates)
- `memory/__init__.py` — package marker
- `memory/db.py` — SQLite `connect()` helper (WAL, foreign keys, row factory)
- `memory/runner.py` — forward-only SQL migration runner with `schema_meta` tracking
- `migrations/0001_init.sql` — bootstrap: `inbox` and `outbox` queue tables
- `approval/__init__.py`, `scheduler/__init__.py`, `loops/__init__.py`, `tools/__init__.py` — empty markers (populated by later phases)

**Deploy (`deploy/`)**
- `install.sh` — first-run setup: prereq checks → dir tree → config.toml → migrations → claude-config → (stubbed) Keychain → launchd install
- `com.interceder.gateway.plist` — launchd template with `__INTERCEDER_*__` placeholders
- `com.interceder.manager.plist` — same pattern

**Tests (`tests/`)**
- `__init__.py` — package marker
- `conftest.py` — `tmp_interceder_home` fixture isolates tests from the real `~/Library/…`
- `test_config.py` — path resolution + model IDs + service defaults
- `test_db.py` — WAL mode, foreign keys, row factory
- `test_migrations.py` — migration runner unit tests with synthetic migrations
- `test_migrations_real.py` — migration runner integration test against packaged `0001_init.sql`
- `test_gateway.py` — in-process FastAPI tests + out-of-process subprocess lifecycle
- `test_manager.py` — Supervisor unit test + subprocess lifecycle
- `test_plists.py` — plist parse + required keys
- `test_install_script.py` — install.sh end-to-end in a sandboxed `HOME`

---

## Task 1: Initialize repo + gitignore + Python pin

**Files:**
- Create: `.gitignore`
- Create: `.python-version`

- [ ] **Step 1: Initialize the git repository**

Run:
```bash
cd /Users/marcsinger/Downloads/interceder
git init
```

Expected: `Initialized empty Git repository in …/interceder/.git/`.

- [ ] **Step 2: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
*.egg

# Virtual envs
.venv/
venv/
env/

# uv
.uv/

# Tests
.pytest_cache/
.coverage
htmlcov/

# IDE / OS
.vscode/
.idea/
*.swp
.DS_Store

# Interceder local state (tests, sandboxes)
/tmp/
*.sqlite
*.sqlite-wal
*.sqlite-shm
/.interceder-home/
```

- [ ] **Step 3: Write `.python-version`**

```
3.12
```

- [ ] **Step 4: First commit**

Run:
```bash
git add .gitignore .python-version plan.md
git commit -m "chore: initial scaffolding — gitignore, python pin, spec"
```

---

## Task 2: `pyproject.toml` + `uv sync`

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "interceder"
version = "0.0.1"
description = "Remote Claude Code harness — Slack + webapp over Tailscale"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "click>=8.1",
    "keyring>=25.0",
]

[project.scripts]
interceder = "interceder.__main__:main"

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-timeout>=2.3",
    "httpx>=0.27",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/interceder"]

[tool.hatch.build.targets.wheel.force-include]
"src/interceder/migrations" = "interceder/migrations"

[tool.pytest.ini_options]
testpaths = ["tests"]
timeout = 30
```

Notes:
- Slack (`slack-bolt`) and Claude (`claude-agent-sdk`) are deliberately **not** added in Phase 0 — they arrive in Phases 1 and 2 respectively. Keeping Phase 0 deps minimal avoids dep-resolution friction before anything even imports those packages.
- `force-include` ensures `*.sql` migration files are packaged into the wheel.

- [ ] **Step 2: Resolve and install deps**

Run:
```bash
uv sync
```

Expected: creates `.venv/`, produces `uv.lock`, installs FastAPI, uvicorn, click, pydantic, keyring, pytest, pytest-timeout, httpx. Warns that no source tree exists yet — that's fine.

- [ ] **Step 3: Commit pyproject + lockfile**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: pyproject with fastapi + uvicorn + click + pytest"
```

---

## Task 3: Package skeleton + click CLI dispatcher

**Files:**
- Create: `src/interceder/__init__.py`
- Create: `src/interceder/__main__.py`
- Create: `src/interceder/gateway/__init__.py`
- Create: `src/interceder/manager/__init__.py`
- Create: `src/interceder/worker/__init__.py`
- Create: `src/interceder/memory/__init__.py`
- Create: `src/interceder/migrations/__init__.py`
- Create: `src/interceder/approval/__init__.py`
- Create: `src/interceder/scheduler/__init__.py`
- Create: `src/interceder/loops/__init__.py`
- Create: `src/interceder/tools/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create the source and test directory tree**

Run:
```bash
mkdir -p src/interceder/gateway \
         src/interceder/manager \
         src/interceder/worker \
         src/interceder/memory \
         src/interceder/migrations \
         src/interceder/approval \
         src/interceder/scheduler \
         src/interceder/loops \
         src/interceder/tools \
         tests deploy
```

- [ ] **Step 2: Create empty package markers**

Run:
```bash
touch src/interceder/__init__.py \
      src/interceder/gateway/__init__.py \
      src/interceder/manager/__init__.py \
      src/interceder/worker/__init__.py \
      src/interceder/memory/__init__.py \
      src/interceder/migrations/__init__.py \
      src/interceder/approval/__init__.py \
      src/interceder/scheduler/__init__.py \
      src/interceder/loops/__init__.py \
      src/interceder/tools/__init__.py \
      tests/__init__.py
```

- [ ] **Step 3: Write the CLI dispatcher `src/interceder/__main__.py`**

```python
"""Interceder CLI — dispatches to gateway, manager, migrate subcommands."""
from __future__ import annotations

import click


@click.group()
def main() -> None:
    """Interceder command-line entrypoint."""


@main.command()
def gateway() -> None:
    """Run the Gateway service (foreground, for launchd)."""
    from interceder.gateway.service import run

    run()


@main.command()
def manager() -> None:
    """Run the Manager Supervisor service (foreground, for launchd)."""
    from interceder.manager.service import run

    run()


@main.command()
@click.option("--db", "db_path", default=None, help="Override DB path.")
def migrate(db_path: str | None) -> None:
    """Apply all pending SQL migrations forward."""
    from interceder.memory.runner import migrate as do_migrate

    version = do_migrate(db_path_override=db_path)
    click.echo(f"migrations applied — schema version now {version}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write `tests/conftest.py` with the `tmp_interceder_home` fixture**

```python
"""Shared pytest fixtures for Interceder tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_interceder_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate tests into a temporary INTERCEDER_HOME."""
    home = tmp_path / "interceder-home"
    home.mkdir()
    monkeypatch.setenv("INTERCEDER_HOME", str(home))
    return home
```

- [ ] **Step 5: Sync and verify package imports**

Run:
```bash
uv sync
uv run python -c "import interceder, interceder.gateway, interceder.manager, interceder.memory, interceder.worker; print('ok')"
```

Expected: `ok` on stdout.

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat: package skeleton + click CLI dispatcher + conftest"
```

---

## Task 4: `config.py` — paths, model IDs, service defaults

**Files:**
- Create: `src/interceder/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests `tests/test_config.py`**

```python
"""Tests for interceder.config — paths, model IDs, and service defaults."""
from __future__ import annotations

from pathlib import Path

import pytest

from interceder import config


def test_interceder_home_env_override(tmp_interceder_home: Path) -> None:
    """INTERCEDER_HOME env var takes precedence over the default path."""
    assert config.interceder_home() == tmp_interceder_home


def test_interceder_home_default_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With env unset, home defaults to ~/Library/Application Support/Interceder."""
    monkeypatch.delenv("INTERCEDER_HOME", raising=False)
    expected = Path("~/Library/Application Support/Interceder").expanduser()
    assert config.interceder_home() == expected


def test_paths_are_derived_from_home(tmp_interceder_home: Path) -> None:
    """DB, blobs, claude-config, workers, logs all live under home."""
    home = tmp_interceder_home
    assert config.db_path() == home / "db" / "memory.sqlite"
    assert config.blobs_dir() == home / "blobs"
    assert config.claude_config_dir() == home / "claude-config"
    assert config.workers_dir() == home / "workers"
    assert config.logs_dir() == home / "logs"
    assert config.config_toml_path() == home / "config.toml"


def test_migrations_dir_is_packaged(tmp_interceder_home: Path) -> None:
    """The migrations directory ships inside the package."""
    mig = config.migrations_dir()
    assert mig.is_dir()
    assert mig.name == "migrations"
    assert mig.parent.name == "interceder"


def test_model_ids_are_defined() -> None:
    """Every model ID referenced by the spec lives in one module (N18)."""
    assert config.MANAGER_MODEL == "claude-opus-4-6"
    assert config.WORKER_DEFAULT_MODEL == "claude-sonnet-4-6"
    assert config.CLASSIFIER_MODEL == "claude-haiku-4-5-20251001"


def test_gateway_bind_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gateway bind host/port have sane defaults and are env-overridable."""
    monkeypatch.delenv("INTERCEDER_GATEWAY_HOST", raising=False)
    monkeypatch.delenv("INTERCEDER_GATEWAY_PORT", raising=False)
    assert config.gateway_bind_host() == "127.0.0.1"
    assert config.gateway_bind_port() == 7878

    monkeypatch.setenv("INTERCEDER_GATEWAY_HOST", "100.64.1.2")
    monkeypatch.setenv("INTERCEDER_GATEWAY_PORT", "9999")
    assert config.gateway_bind_host() == "100.64.1.2"
    assert config.gateway_bind_port() == 9999
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with `AttributeError` / `ImportError`.

- [ ] **Step 3: Write `src/interceder/config.py`**

```python
"""Central configuration: paths, model IDs, service defaults.

N18: all Claude/model IDs live in this module so upgrades are one-line
changes. All path and env var lookups are functions (not module-level
constants) so tests can monkeypatch the environment freely.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# ----------------------------------------------------------------------
# Model IDs — single source of truth
# ----------------------------------------------------------------------
MANAGER_MODEL: Final[str] = "claude-opus-4-6"
WORKER_DEFAULT_MODEL: Final[str] = "claude-sonnet-4-6"
CLASSIFIER_MODEL: Final[str] = "claude-haiku-4-5-20251001"


# ----------------------------------------------------------------------
# Filesystem paths
# ----------------------------------------------------------------------
_DEFAULT_HOME = Path("~/Library/Application Support/Interceder").expanduser()


def interceder_home() -> Path:
    """Return the Interceder home directory.

    Honors the INTERCEDER_HOME env var so tests can isolate into tmp dirs.
    """
    override = os.environ.get("INTERCEDER_HOME")
    if override:
        return Path(override).expanduser()
    return _DEFAULT_HOME


def db_path() -> Path:
    return interceder_home() / "db" / "memory.sqlite"


def blobs_dir() -> Path:
    return interceder_home() / "blobs"


def claude_config_dir() -> Path:
    return interceder_home() / "claude-config"


def workers_dir() -> Path:
    return interceder_home() / "workers"


def logs_dir() -> Path:
    return interceder_home() / "logs"


def config_toml_path() -> Path:
    return interceder_home() / "config.toml"


def migrations_dir() -> Path:
    """Path to the packaged SQL migrations directory."""
    return Path(__file__).parent / "migrations"


# ----------------------------------------------------------------------
# Gateway bind defaults (overridable via env for tests and launchd)
# ----------------------------------------------------------------------
def gateway_bind_host() -> str:
    return os.environ.get("INTERCEDER_GATEWAY_HOST", "127.0.0.1")


def gateway_bind_port() -> int:
    return int(os.environ.get("INTERCEDER_GATEWAY_PORT", "7878"))
```

- [ ] **Step 4: Run tests, confirm pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/interceder/config.py tests/test_config.py
git commit -m "feat: config module — paths, model IDs, gateway bind defaults"
```

---

## Task 5: SQLite connection helper with WAL mode

**Files:**
- Create: `src/interceder/memory/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests `tests/test_db.py`**

```python
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
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `uv run pytest tests/test_db.py -v`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Write `src/interceder/memory/db.py`**

```python
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
```

- [ ] **Step 4: Run tests, confirm pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/interceder/memory/db.py tests/test_db.py
git commit -m "feat: SQLite connect() helper with WAL mode + foreign keys"
```

---

## Task 6: Forward-only SQL migration runner

**Files:**
- Create: `src/interceder/memory/runner.py`
- Create: `tests/test_migrations.py`

- [ ] **Step 1: Write failing tests `tests/test_migrations.py`**

```python
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
```

- [ ] **Step 2: Run tests, confirm failure**

Run: `uv run pytest tests/test_migrations.py -v`
Expected: FAIL (`ImportError` for `runner`).

- [ ] **Step 3: Write `src/interceder/memory/runner.py`**

```python
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
    try:
        conn.execute("BEGIN")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_meta (version, applied_at) VALUES (?, ?)",
            (version, int(time.time())),
        )
        conn.execute("COMMIT")
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
```

- [ ] **Step 4: Run tests, confirm pass**

Run: `uv run pytest tests/test_migrations.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/interceder/memory/runner.py tests/test_migrations.py
git commit -m "feat: forward-only SQL migration runner with schema_meta tracking"
```

---

## Task 7: First real migration — `0001_init.sql`

The packaged migration the installer will actually apply. Phase 0 scope = the two queue tables that the Gateway↔Manager architecture needs to exist from day one. The full memory archive (`messages`, FTS5, entities, etc.) arrives in Phase 3 as `0002_memory_archive.sql`.

**Files:**
- Create: `src/interceder/migrations/0001_init.sql`
- Create: `tests/test_migrations_real.py`

- [ ] **Step 1: Write failing integration test `tests/test_migrations_real.py`**

```python
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
```

- [ ] **Step 2: Run tests, confirm failure**

Run: `uv run pytest tests/test_migrations_real.py -v`
Expected: FAIL — migrations dir is empty, runner returns version 0.

- [ ] **Step 3: Write `src/interceder/migrations/0001_init.sql`**

```sql
-- 0001_init.sql — bootstrap the Interceder memory database.
--
-- Phase 0 scope: the two durable queue tables that bridge the Gateway and
-- the Manager Supervisor. The full memory archive (messages/FTS5, entities,
-- facts, reflections, workers, approvals, schedules, loops, costs) arrives
-- in later phases as additional migration files (0002 onward).

-- Inbox: Gateway writes here; Manager Supervisor drains it.
CREATE TABLE inbox (
    id              TEXT PRIMARY KEY,                -- UUID, idempotency key
    correlation_id  TEXT NOT NULL,
    user_id         TEXT NOT NULL DEFAULT 'me',
    source          TEXT NOT NULL,                   -- slack|webapp|scheduler:*|...
    kind            TEXT NOT NULL,                   -- text|attachment|approval_resolution|...
    content         TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'queued',  -- queued|in_flight|completed|failed
    in_flight_pid   INTEGER,
    created_at      INTEGER NOT NULL,
    processed_at    INTEGER
);
CREATE INDEX idx_inbox_status_created ON inbox(status, created_at);
CREATE INDEX idx_inbox_correlation   ON inbox(correlation_id);

-- Outbox: Manager writes here; Gateway drains it to Slack and webapp.
CREATE TABLE outbox (
    id              TEXT PRIMARY KEY,
    correlation_id  TEXT NOT NULL,
    inbox_id        TEXT,                            -- nullable: proactives have no inbox origin
    source          TEXT NOT NULL,                   -- manager|manager_proactive|worker_event|approval
    kind            TEXT NOT NULL,                   -- text|tool_result|approval_request|worker_update|proactive
    content         TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'queued',  -- queued|in_flight|delivered|failed
    delivered_slack INTEGER NOT NULL DEFAULT 0,
    delivered_web   INTEGER NOT NULL DEFAULT 0,
    created_at      INTEGER NOT NULL,
    delivered_at    INTEGER
);
CREATE INDEX idx_outbox_status_created ON outbox(status, created_at);
CREATE INDEX idx_outbox_correlation   ON outbox(correlation_id);
```

- [ ] **Step 4: Run tests, confirm pass**

Run: `uv run pytest tests/test_migrations_real.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/interceder/migrations/0001_init.sql tests/test_migrations_real.py
git commit -m "feat: 0001 migration — inbox and outbox queue tables"
```

---

## Task 8: Gateway service skeleton

FastAPI app with a health endpoint + a placeholder root, plus a uvicorn Server entry point that installs signal handlers for clean SIGTERM shutdown.

**Files:**
- Create: `src/interceder/gateway/app.py`
- Create: `src/interceder/gateway/service.py`
- Create: `tests/test_gateway.py`

- [ ] **Step 1: Write failing tests `tests/test_gateway.py`**

```python
"""Tests for the Gateway FastAPI app and service lifecycle."""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from interceder.gateway.app import build_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(build_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "gateway"


def test_root_serves_placeholder_html() -> None:
    client = TestClient(build_app())
    resp = client.get("/")
    assert resp.status_code == 200
    assert "interceder" in resp.text.lower()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.timeout(25)
def test_gateway_service_starts_and_stops_on_sigterm(
    tmp_interceder_home: Path,
) -> None:
    port = _free_port()
    env = {
        **os.environ,
        "INTERCEDER_HOME": str(tmp_interceder_home),
        "INTERCEDER_GATEWAY_HOST": "127.0.0.1",
        "INTERCEDER_GATEWAY_PORT": str(port),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "interceder", "gateway"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Poll /health until ready (or timeout).
        deadline = time.monotonic() + 10
        ready = False
        while time.monotonic() < deadline:
            try:
                r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                if r.status_code == 200:
                    ready = True
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        if not ready:
            proc.kill()
            out, err = proc.communicate()
            pytest.fail(
                f"gateway never became ready\nstdout: {out.decode()}\n"
                f"stderr: {err.decode()}"
            )

        proc.send_signal(signal.SIGTERM)
        try:
            rc = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("gateway did not exit within 10s of SIGTERM")
        assert rc == 0, f"gateway exited with code {rc}"
    finally:
        if proc.poll() is None:
            proc.kill()
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `uv run pytest tests/test_gateway.py -v`
Expected: FAIL — `interceder.gateway.app` doesn't exist.

- [ ] **Step 3: Write `src/interceder/gateway/app.py`**

```python
"""FastAPI app factory for the Gateway service.

Phase 0: serves a health endpoint and a placeholder root. Slack Socket
Mode and the webapp WebSocket endpoint arrive in Phases 1 and 6
respectively.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


def build_app() -> FastAPI:
    app = FastAPI(title="Interceder Gateway", version="0.0.1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "gateway"}

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        return (
            "<!doctype html><html><head><title>Interceder</title></head>"
            "<body><h1>Interceder Gateway</h1>"
            "<p>Phase 0 skeleton. The webapp arrives in Phase 6.</p>"
            "</body></html>"
        )

    return app
```

- [ ] **Step 4: Write `src/interceder/gateway/service.py`**

```python
"""Gateway service entry — launchd-managed long-lived process."""
from __future__ import annotations

import logging

import uvicorn

from interceder import config
from interceder.gateway.app import build_app

log = logging.getLogger("interceder.gateway")


def run() -> None:
    """Boot the Gateway FastAPI app under uvicorn in the foreground.

    uvicorn installs its own SIGINT/SIGTERM handlers that set
    `Server.should_exit = True`, so Ctrl-C and `launchctl kickstart -k`
    both shut it down cleanly.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    host = config.gateway_bind_host()
    port = config.gateway_bind_port()
    log.info("starting gateway on %s:%d", host, port)

    uv_config = uvicorn.Config(
        build_app(),
        host=host,
        port=port,
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(uv_config)
    server.run()
    log.info("gateway shut down cleanly")
```

- [ ] **Step 5: Run tests, confirm pass**

Run: `uv run pytest tests/test_gateway.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/interceder/gateway/app.py src/interceder/gateway/service.py tests/test_gateway.py
git commit -m "feat: gateway skeleton — FastAPI app, health endpoint, uvicorn entry"
```

---

## Task 9: Manager Supervisor skeleton

The Supervisor is Phase 0's stand-in for what Phase 2 turns into a Claude Agent SDK wrapper. For now it opens the SQLite DB on start, runs a tick loop (no-op heartbeat), and shuts down cleanly on signal.

**Files:**
- Create: `src/interceder/manager/supervisor.py`
- Create: `src/interceder/manager/service.py`
- Create: `tests/test_manager.py`

- [ ] **Step 1: Write failing tests `tests/test_manager.py`**

```python
"""Tests for the Manager Supervisor and its service lifecycle."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from interceder import config
from interceder.manager.supervisor import Supervisor


def test_supervisor_start_opens_db(tmp_interceder_home: Path) -> None:
    # Migrations must run first so db.connect() has a schema to open.
    from interceder.memory import runner

    runner.migrate()

    sup = Supervisor()
    sup.start()
    try:
        assert sup.is_running
        assert config.db_path().exists()
    finally:
        sup.stop()
    assert not sup.is_running


def test_supervisor_tick_is_safe_when_running(tmp_interceder_home: Path) -> None:
    from interceder.memory import runner

    runner.migrate()
    sup = Supervisor()
    sup.start()
    try:
        for _ in range(5):
            sup.tick()  # no-op heartbeat, must not raise
    finally:
        sup.stop()


def test_supervisor_tick_is_noop_when_stopped(tmp_interceder_home: Path) -> None:
    sup = Supervisor()
    # tick() before start() must not raise and must not open resources
    sup.tick()
    assert not sup.is_running


@pytest.mark.timeout(25)
def test_manager_service_starts_and_stops_on_sigterm(
    tmp_interceder_home: Path,
) -> None:
    env = {**os.environ, "INTERCEDER_HOME": str(tmp_interceder_home)}
    # Bootstrap the DB so the Supervisor has a schema to open.
    subprocess.run(
        [sys.executable, "-m", "interceder", "migrate"], env=env, check=True
    )

    proc = subprocess.Popen(
        [sys.executable, "-m", "interceder", "manager"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Let the Supervisor reach its main loop. 1.5s is plenty for a local
        # Python import + db.connect() + one tick.
        time.sleep(1.5)
        assert proc.poll() is None, (
            f"manager crashed on startup; stderr:\n{proc.stderr.read().decode()}"
        )

        proc.send_signal(signal.SIGTERM)
        try:
            rc = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("manager did not exit within 10s of SIGTERM")
        assert rc == 0, f"manager exited with code {rc}"
    finally:
        if proc.poll() is None:
            proc.kill()
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `uv run pytest tests/test_manager.py -v`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Write `src/interceder/manager/supervisor.py`**

```python
"""Manager Supervisor — Phase 0 skeleton.

Phase 2 will grow this into a wrapper around a long-lived Claude Agent SDK
session, with the hot memory curator, tool registrations, inbox-drain loop,
worker supervision, and rate-limit backoff. For Phase 0, it just proves
the supervision loop can boot, open the DB, tick harmlessly, and shut
down cleanly.
"""
from __future__ import annotations

import logging
import sqlite3

from interceder import config
from interceder.memory import db

log = logging.getLogger("interceder.manager.supervisor")


class Supervisor:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        log.info("supervisor starting; db=%s", config.db_path())
        self._conn = db.connect(config.db_path())
        self._running = True
        log.info("supervisor started")

    def tick(self) -> None:
        """One pass of the main loop. Phase 0: no-op heartbeat."""
        if not self._running:
            return
        log.debug("supervisor tick")

    def stop(self) -> None:
        if not self._running and self._conn is None:
            return
        log.info("supervisor stopping")
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._running = False
        log.info("supervisor stopped")
```

- [ ] **Step 4: Write `src/interceder/manager/service.py`**

```python
"""Manager Supervisor service entry — launchd-managed long-lived process."""
from __future__ import annotations

import logging
import signal
import threading

from interceder.manager.supervisor import Supervisor

log = logging.getLogger("interceder.manager")

_TICK_INTERVAL_SEC = 1.0


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    supervisor = Supervisor()
    supervisor.start()

    stop_event = threading.Event()

    def _handle_signal(signum: int, _frame: object) -> None:  # noqa: ARG001
        log.info("received signal %d — requesting shutdown", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        while not stop_event.is_set():
            supervisor.tick()
            stop_event.wait(_TICK_INTERVAL_SEC)
    finally:
        supervisor.stop()
    log.info("manager shut down cleanly")
```

- [ ] **Step 5: Run tests, confirm pass**

Run: `uv run pytest tests/test_manager.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/interceder/manager/supervisor.py src/interceder/manager/service.py tests/test_manager.py
git commit -m "feat: manager supervisor skeleton — tick loop + SIGTERM handling"
```

---

## Task 10: launchd plist templates

These are templates with `__INTERCEDER_*__` placeholders; `install.sh` substitutes the values when installing into `~/Library/LaunchAgents/`.

**Files:**
- Create: `deploy/com.interceder.gateway.plist`
- Create: `deploy/com.interceder.manager.plist`
- Create: `tests/test_plists.py`

- [ ] **Step 1: Write failing tests `tests/test_plists.py`**

```python
"""Verify the launchd plist templates parse and contain required keys."""
from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY = REPO_ROOT / "deploy"


@pytest.mark.parametrize(
    "plist_name,label",
    [
        ("com.interceder.gateway.plist", "com.interceder.gateway"),
        ("com.interceder.manager.plist", "com.interceder.manager"),
    ],
)
def test_plist_has_required_keys(plist_name: str, label: str) -> None:
    path = DEPLOY / plist_name
    assert path.exists(), f"missing {plist_name}"
    with path.open("rb") as f:
        data = plistlib.load(f)

    assert data["Label"] == label
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] is True
    assert isinstance(data["ProgramArguments"], list)
    assert len(data["ProgramArguments"]) >= 1
    assert "StandardOutPath" in data
    assert "StandardErrorPath" in data
    env = data["EnvironmentVariables"]
    assert "INTERCEDER_HOME" in env


def test_gateway_plist_references_gateway_subcommand() -> None:
    with (DEPLOY / "com.interceder.gateway.plist").open("rb") as f:
        data = plistlib.load(f)
    assert "gateway" in data["ProgramArguments"]


def test_manager_plist_references_manager_subcommand() -> None:
    with (DEPLOY / "com.interceder.manager.plist").open("rb") as f:
        data = plistlib.load(f)
    assert "manager" in data["ProgramArguments"]
```

- [ ] **Step 2: Run tests, confirm failure**

Run: `uv run pytest tests/test_plists.py -v`
Expected: FAIL (plists missing).

- [ ] **Step 3: Write `deploy/com.interceder.gateway.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.interceder.gateway</string>

    <key>ProgramArguments</key>
    <array>
        <string>__INTERCEDER_UV_BIN__</string>
        <string>run</string>
        <string>--project</string>
        <string>__INTERCEDER_REPO__</string>
        <string>python</string>
        <string>-m</string>
        <string>interceder</string>
        <string>gateway</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>INTERCEDER_HOME</key>
        <string>__INTERCEDER_HOME__</string>
        <key>INTERCEDER_GATEWAY_HOST</key>
        <string>127.0.0.1</string>
        <key>INTERCEDER_GATEWAY_PORT</key>
        <string>7878</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>

    <key>StandardOutPath</key>
    <string>__INTERCEDER_HOME__/logs/gateway.log</string>
    <key>StandardErrorPath</key>
    <string>__INTERCEDER_HOME__/logs/gateway.err.log</string>

    <key>WorkingDirectory</key>
    <string>__INTERCEDER_REPO__</string>
</dict>
</plist>
```

- [ ] **Step 4: Write `deploy/com.interceder.manager.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.interceder.manager</string>

    <key>ProgramArguments</key>
    <array>
        <string>__INTERCEDER_UV_BIN__</string>
        <string>run</string>
        <string>--project</string>
        <string>__INTERCEDER_REPO__</string>
        <string>python</string>
        <string>-m</string>
        <string>interceder</string>
        <string>manager</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>INTERCEDER_HOME</key>
        <string>__INTERCEDER_HOME__</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>

    <key>StandardOutPath</key>
    <string>__INTERCEDER_HOME__/logs/manager.log</string>
    <key>StandardErrorPath</key>
    <string>__INTERCEDER_HOME__/logs/manager.err.log</string>

    <key>WorkingDirectory</key>
    <string>__INTERCEDER_REPO__</string>
</dict>
</plist>
```

- [ ] **Step 5: Run tests, confirm pass**

Run: `uv run pytest tests/test_plists.py -v`
Expected: 4 passed.

Note: `plistlib` treats `__INTERCEDER_HOME__` etc. as ordinary strings, so the templates parse even before substitution.

- [ ] **Step 6: Commit**

```bash
git add deploy/com.interceder.gateway.plist deploy/com.interceder.manager.plist tests/test_plists.py
git commit -m "feat: launchd plist templates for gateway and manager"
```

---

## Task 11: `install.sh` — first-run setup

Bash orchestrator that calls the Python migration runner for the heavy lifting. Testable end-to-end in a sandboxed `HOME` via three opt-out env vars: `INTERCEDER_SKIP_PREREQ_CHECKS`, `INTERCEDER_SKIP_KEYCHAIN`, `INTERCEDER_SKIP_LAUNCHD`. The tests use all three.

**Files:**
- Create: `deploy/install.sh`
- Create: `tests/test_install_script.py`

- [ ] **Step 1: Write failing tests `tests/test_install_script.py`**

```python
"""End-to-end test for deploy/install.sh in a sandboxed HOME."""
from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "deploy" / "install.sh"


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    fake = tmp_path / "fake-home"
    (fake / "Library" / "Application Support").mkdir(parents=True)
    (fake / "Library" / "LaunchAgents").mkdir(parents=True)
    return fake


def _run_install(fake_home: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "HOME": str(fake_home),
        "INTERCEDER_SKIP_LAUNCHD": "1",
        "INTERCEDER_SKIP_KEYCHAIN": "1",
        "INTERCEDER_SKIP_PREREQ_CHECKS": "1",
    }
    return subprocess.run(
        ["bash", str(INSTALL_SH)],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_install_creates_directory_tree(fake_home: Path) -> None:
    result = _run_install(fake_home)
    assert result.returncode == 0, (
        f"install.sh failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    home = fake_home / "Library" / "Application Support" / "Interceder"
    for sub in (
        "db",
        "blobs",
        "claude-config",
        "claude-config/skills",
        "claude-config/agents",
        "claude-config/plugins",
        "workers",
        "logs",
    ):
        assert (home / sub).is_dir(), f"missing {sub}"
    assert (home / "config.toml").exists()


def test_install_bootstraps_memory_db(fake_home: Path) -> None:
    result = _run_install(fake_home)
    assert result.returncode == 0
    home = fake_home / "Library" / "Application Support" / "Interceder"
    db_file = home / "db" / "memory.sqlite"
    assert db_file.exists()

    conn = sqlite3.connect(db_file)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"schema_meta", "inbox", "outbox"}.issubset(tables)
        version = conn.execute(
            "SELECT MAX(version) FROM schema_meta"
        ).fetchone()[0]
        assert version == 1
    finally:
        conn.close()


def test_install_seeds_claude_config(fake_home: Path) -> None:
    result = _run_install(fake_home)
    assert result.returncode == 0
    home = fake_home / "Library" / "Application Support" / "Interceder"
    settings = home / "claude-config" / "settings.json"
    assert settings.exists()
    assert "interceder" in settings.read_text().lower()

    skills_git = home / "claude-config" / "skills" / ".git"
    assert skills_git.is_dir(), "skills/ must be a git repo"


def test_install_is_idempotent(fake_home: Path) -> None:
    first = _run_install(fake_home)
    assert first.returncode == 0, first.stderr
    second = _run_install(fake_home)
    assert second.returncode == 0, second.stderr
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `uv run pytest tests/test_install_script.py -v`
Expected: FAIL (install.sh missing).

- [ ] **Step 3: Write `deploy/install.sh`**

```bash
#!/usr/bin/env bash
# deploy/install.sh — first-run setup for Interceder on macOS.
#
# Opt-out env vars (all default to unset/0):
#   INTERCEDER_SKIP_PREREQ_CHECKS  — bypass tool / version checks
#   INTERCEDER_SKIP_KEYCHAIN        — don't prompt for Slack/Veo/Gemini secrets
#   INTERCEDER_SKIP_LAUNCHD         — don't install or load launchd plists
#
# The directory tree under $HOME/Library/Application Support/Interceder is
# always created, config.toml is written if absent, migrations are always
# applied, and claude-config/ is always seeded.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERCEDER_HOME="${HOME}/Library/Application Support/Interceder"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"

log()  { printf '[install] %s\n' "$*"; }
die()  { printf '[install] ERROR: %s\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------------
# 1. Prerequisite checks
# --------------------------------------------------------------------
check_prereqs() {
    if [[ "${INTERCEDER_SKIP_PREREQ_CHECKS:-0}" == "1" ]]; then
        log "skipping prerequisite checks"
        return 0
    fi
    [[ "$(uname -s)" == "Darwin" ]] || die "macOS only"
    command -v python3 >/dev/null || die "python3 not found"
    local py_version
    py_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    case "${py_version}" in
        3.12|3.13) ;;
        *) die "Python 3.12 or 3.13 required (found ${py_version})" ;;
    esac
    command -v git >/dev/null || die "git not found"
    command -v uv  >/dev/null || die "uv not found — install from https://docs.astral.sh/uv/"
    command -v tailscale >/dev/null || log "WARNING: tailscale not found — webapp will be unreachable"
    command -v claude    >/dev/null || log "WARNING: claude CLI not found — Manager will not be able to reason"
}

# --------------------------------------------------------------------
# 2. Directory tree
# --------------------------------------------------------------------
make_dirs() {
    log "creating ${INTERCEDER_HOME}"
    mkdir -p \
        "${INTERCEDER_HOME}/db" \
        "${INTERCEDER_HOME}/blobs" \
        "${INTERCEDER_HOME}/claude-config/skills" \
        "${INTERCEDER_HOME}/claude-config/agents" \
        "${INTERCEDER_HOME}/claude-config/plugins" \
        "${INTERCEDER_HOME}/workers" \
        "${INTERCEDER_HOME}/logs"
}

# --------------------------------------------------------------------
# 3. config.toml
# --------------------------------------------------------------------
write_config_toml() {
    local cfg="${INTERCEDER_HOME}/config.toml"
    if [[ -f "${cfg}" ]]; then
        log "config.toml already exists; leaving it alone"
        return 0
    fi
    log "writing default config.toml"
    cat > "${cfg}" <<'TOML'
# Interceder configuration. Non-secret values only.
# Secrets live in the macOS Keychain under service name "Interceder".

[general]
user_id = "me"

[allowlist]
# Add repo roots here, e.g. paths = ["~/code/repoA", "~/code/repoB"]
paths = []

[quiet_hours]
start = "23:00"
end   = "07:00"
timezone = "local"

[proactive.rate_limit_seconds]
worker_done       = 30
approval          = 0
failure           = 0
idle_reflection   = 900
opportunistic     = 3600

[secrets]
# Keychain entry names (not values).
slack_bot_token = "interceder/slack_bot_token"
slack_app_token = "interceder/slack_app_token"
webapp_jwt_key  = "interceder/webapp_jwt_key"
veo_api_key     = "interceder/veo_api_key"
gemini_api_key  = "interceder/gemini_api_key"
TOML
}

# --------------------------------------------------------------------
# 4. memory.sqlite bootstrap via the Python migration runner
# --------------------------------------------------------------------
run_migrations() {
    log "running migrations"
    (
        cd "${REPO_ROOT}"
        INTERCEDER_HOME="${INTERCEDER_HOME}" uv run python -m interceder migrate
    )
}

# --------------------------------------------------------------------
# 5. Claude config scaffolding
# --------------------------------------------------------------------
seed_claude_config() {
    local cc="${INTERCEDER_HOME}/claude-config"
    local settings="${cc}/settings.json"
    if [[ ! -f "${settings}" ]]; then
        log "writing claude-config/settings.json"
        cat > "${settings}" <<'JSON'
{
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "name": "interceder",
    "description": "Interceder harness Claude config — isolated from the user's personal ~/.claude/",
    "permissions": {
        "allow": [],
        "deny": []
    },
    "skills": {
        "directories": ["./skills"]
    }
}
JSON
    fi

    local skills="${cc}/skills"
    if [[ ! -d "${skills}/.git" ]]; then
        log "initializing skills/ git repo"
        (
            cd "${skills}"
            git init -q
            git -c user.email=interceder@localhost -c user.name=Interceder commit \
                --allow-empty -q -m "chore: seed Interceder skill library"
        )
    fi
}

# --------------------------------------------------------------------
# 6. Keychain prompts (stub — real prompts arrive with Phase 1 Slack)
# --------------------------------------------------------------------
prompt_keychain() {
    if [[ "${INTERCEDER_SKIP_KEYCHAIN:-0}" == "1" ]]; then
        log "skipping Keychain prompts"
        return 0
    fi
    log "Keychain setup deferred — run 'interceder setup-secrets' after Phase 1 lands Slack support"
}

# --------------------------------------------------------------------
# 7. launchd plist install
# --------------------------------------------------------------------
install_launchd() {
    if [[ "${INTERCEDER_SKIP_LAUNCHD:-0}" == "1" ]]; then
        log "skipping launchd install"
        return 0
    fi
    mkdir -p "${LAUNCH_AGENTS_DIR}"
    local uv_bin
    uv_bin="$(command -v uv)"
    for name in gateway manager; do
        local src="${REPO_ROOT}/deploy/com.interceder.${name}.plist"
        local dst="${LAUNCH_AGENTS_DIR}/com.interceder.${name}.plist"
        log "installing ${dst}"
        sed \
            -e "s|__INTERCEDER_HOME__|${INTERCEDER_HOME}|g" \
            -e "s|__INTERCEDER_REPO__|${REPO_ROOT}|g" \
            -e "s|__INTERCEDER_UV_BIN__|${uv_bin}|g" \
            "${src}" > "${dst}"
        # Unload if already loaded so we pick up changes on reruns.
        launchctl unload "${dst}" >/dev/null 2>&1 || true
        launchctl load "${dst}"
    done
}

main() {
    check_prereqs
    make_dirs
    write_config_toml
    run_migrations
    seed_claude_config
    prompt_keychain
    install_launchd
    log "install complete — INTERCEDER_HOME=${INTERCEDER_HOME}"
}

main "$@"
```

- [ ] **Step 4: Make `install.sh` executable**

Run:
```bash
chmod +x deploy/install.sh
```

- [ ] **Step 5: Run the install tests**

Run: `uv run pytest tests/test_install_script.py -v`
Expected: 4 passed.

If the test fails because `uv run` inside the nested subprocess can't find the project, re-check that `INTERCEDER_SKIP_PREREQ_CHECKS=1` is set and that `cd "${REPO_ROOT}"` runs before the `uv run` invocation in `run_migrations`.

- [ ] **Step 6: Commit**

```bash
git add deploy/install.sh tests/test_install_script.py
git commit -m "feat: install.sh — directory tree, migrations, claude-config scaffolding, launchd install"
```

---

## Task 12: Phase 0 end-to-end validation

Manual smoke test of the full Phase 0 outcome: install into a sandbox HOME, boot the gateway, hit `/health`, boot the manager, send SIGTERM to both, verify clean exits.

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -v`
Expected: every test from Tasks 4–11 passes. Exact count: ~26 tests (6 config + 4 db + 6 migrations unit + 2 migrations real + 3 gateway + 4 manager + 4 plists + 4 install = ~33). The exact number does not matter; **zero failures is the bar**.

- [ ] **Step 2: Manually run install.sh into a sandbox HOME**

Run:
```bash
rm -rf /tmp/interceder-phase0-home
mkdir -p "/tmp/interceder-phase0-home/Library/Application Support" \
         "/tmp/interceder-phase0-home/Library/LaunchAgents"
HOME=/tmp/interceder-phase0-home \
INTERCEDER_SKIP_LAUNCHD=1 \
INTERCEDER_SKIP_KEYCHAIN=1 \
INTERCEDER_SKIP_PREREQ_CHECKS=1 \
    bash deploy/install.sh
```

Expected final line: `[install] install complete — INTERCEDER_HOME=/tmp/interceder-phase0-home/Library/Application Support/Interceder`.
Expected tree:
```
/tmp/interceder-phase0-home/Library/Application Support/Interceder/
├── blobs/
├── claude-config/
│   ├── agents/
│   ├── plugins/
│   ├── settings.json
│   └── skills/  (with .git/)
├── config.toml
├── db/
│   └── memory.sqlite
├── logs/
└── workers/
```

- [ ] **Step 3: Boot the gateway in the sandbox HOME and confirm /health**

Run in terminal A:
```bash
INTERCEDER_HOME="/tmp/interceder-phase0-home/Library/Application Support/Interceder" \
    uv run python -m interceder gateway
```
Expected: log line `starting gateway on 127.0.0.1:7878`.

Run in terminal B:
```bash
curl -s http://127.0.0.1:7878/health
```
Expected: `{"status":"ok","service":"gateway"}`.

Then Ctrl-C the gateway in terminal A.
Expected: log line `gateway shut down cleanly`, process exits with code 0 within ~1 second.

- [ ] **Step 4: Boot the manager in the sandbox HOME**

Run in terminal A:
```bash
INTERCEDER_HOME="/tmp/interceder-phase0-home/Library/Application Support/Interceder" \
    uv run python -m interceder manager
```
Expected logs:
```
… INFO interceder.manager.supervisor supervisor starting; db=…/memory.sqlite
… INFO interceder.manager.supervisor supervisor started
```
The process runs the heartbeat tick loop silently at INFO level.

Send SIGTERM via Ctrl-C.
Expected logs:
```
… INFO interceder.manager received signal 2 — requesting shutdown
… INFO interceder.manager.supervisor supervisor stopping
… INFO interceder.manager.supervisor supervisor stopped
… INFO interceder.manager manager shut down cleanly
```
Exit code: 0.

- [ ] **Step 5: Clean up the sandbox**

Run:
```bash
rm -rf /tmp/interceder-phase0-home
```

- [ ] **Step 6: Final Phase 0 commit**

Run:
```bash
git status
git add -A
git commit --allow-empty -m "chore: phase 0 complete — skeleton boots, migrates, and shuts down cleanly"
```

**Phase 0 done.** Both services boot, the migration runner bootstraps the DB, `install.sh` stands up the whole directory tree from scratch, and everything shuts down cleanly on SIGTERM. Phase 1 (Gateway wires up Slack Socket Mode) is the next plan to write.
