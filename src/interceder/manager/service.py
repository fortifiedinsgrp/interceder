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
