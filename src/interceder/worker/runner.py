"""Worker subprocess entry point.

Invoked as: python -m interceder.worker.runner --task-spec '{"goal":"..."}' --worker-id w-xxx

The worker:
1. Reads the task spec from --task-spec
2. Creates or reuses a sandbox directory
3. Runs an Agent SDK session with the task
4. Streams JSONL events to stdout
5. Exits cleanly when done or on SIGTERM
"""
from __future__ import annotations

import json
import logging
import signal
import sys
import threading

import click

from interceder.worker.protocol import (
    DoneEvent,
    ErrorEvent,
    ProgressEvent,
    serialize_event,
)

log = logging.getLogger("interceder.worker")


def _emit(event: object) -> None:
    """Write a JSONL event to stdout."""
    from interceder.worker.protocol import WorkerEvent

    if isinstance(event, WorkerEvent):
        print(serialize_event(event), flush=True)


@click.command()
@click.option("--task-spec", required=True, help="JSON task specification")
@click.option("--worker-id", required=True, help="Worker ID")
@click.option("--model", default="claude-sonnet-4-6", help="Model to use")
def worker_main(task_spec: str, worker_id: str, model: str) -> None:
    """Run a Worker subprocess."""
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    spec = json.loads(task_spec)
    goal = spec.get("goal", "no goal specified")

    stop_event = threading.Event()

    def _handle_signal(signum: int, _frame: object) -> None:
        log.info("worker %s received signal %d", worker_id, signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _emit(ProgressEvent(worker_id=worker_id, message=f"starting: {goal}", percent=0))

    try:
        # Phase 4: stub execution — real SDK session wiring comes after
        # the Agent SDK is properly integrated
        _emit(ProgressEvent(worker_id=worker_id, message="working...", percent=50))

        if stop_event.is_set():
            _emit(ErrorEvent(worker_id=worker_id, error="interrupted"))
            return

        _emit(DoneEvent(
            worker_id=worker_id,
            summary=f"completed: {goal}",
            diff_ref="",
        ))
    except Exception as exc:
        _emit(ErrorEvent(worker_id=worker_id, error=str(exc)))
        sys.exit(1)


if __name__ == "__main__":
    worker_main()
