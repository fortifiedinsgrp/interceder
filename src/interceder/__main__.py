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
