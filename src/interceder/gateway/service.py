"""Gateway service entry — launchd-managed long-lived process."""
from __future__ import annotations

import logging
import signal
import sys

import uvicorn

from interceder import config
from interceder.gateway.app import build_app

log = logging.getLogger("interceder.gateway")


def run() -> None:
    """Boot the Gateway FastAPI app under uvicorn in the foreground.

    We install a thin SIGTERM handler that asks uvicorn to exit and then
    restores the default disposition so the process exits with code 0
    rather than -15.
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

    original_sigterm = signal.getsignal(signal.SIGTERM)

    def _handle_term(signum: int, frame: object) -> None:
        log.info("received SIGTERM — requesting shutdown")
        server.should_exit = True
        # Restore so we don't re-enter on a second signal.
        signal.signal(signal.SIGTERM, original_sigterm)

    signal.signal(signal.SIGTERM, _handle_term)

    server.run()
    log.info("gateway shut down cleanly")
    sys.exit(0)
