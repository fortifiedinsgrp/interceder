"""Gateway service entry — launchd-managed long-lived process.

Phase 1: starts Slack Socket Mode handler in a background thread alongside
the FastAPI/uvicorn server.
"""
from __future__ import annotations

import logging
import os
import threading

from interceder import config
from interceder.gateway.app import build_app
from interceder.gateway.queue import enqueue_inbox
from interceder.gateway.slack_handler import normalize_slack_event
from interceder.memory import db, runner

log = logging.getLogger("interceder.gateway")


def _start_slack_socket_mode(
    slack_web_client: object,
) -> tuple[threading.Thread | None, object | None]:
    """Start Slack Socket Mode in a background thread. Returns (thread, handler).

    If Slack tokens are not configured, logs a warning and returns (None, None).
    """
    try:
        import keyring
        app_token = keyring.get_password("interceder", "slack_app_token")
        bot_token = keyring.get_password("interceder", "slack_bot_token")
    except Exception:
        app_token = os.environ.get("INTERCEDER_SLACK_APP_TOKEN")
        bot_token = os.environ.get("INTERCEDER_SLACK_BOT_TOKEN")

    if not app_token or not bot_token:
        log.warning("Slack tokens not found — running without Slack")
        return None, None

    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    bolt_app = App(token=bot_token)

    # Open a dedicated DB connection for Slack event handler thread
    conn = db.connect(config.db_path())

    @bolt_app.event("message")
    def handle_message(event: dict, say: object) -> None:
        msg = normalize_slack_event(event)
        if msg is None:
            return
        enqueue_inbox(conn, msg)
        log.info("enqueued inbox: %s", msg.id)
        # Manager will reply via outbox — no canned ack needed

    handler = SocketModeHandler(bolt_app, app_token)

    def _run_socket_mode() -> None:
        try:
            handler.start()
        except Exception:
            log.exception("Slack Socket Mode crashed")

    thread = threading.Thread(target=_run_socket_mode, daemon=True)
    thread.start()
    return thread, handler


def run() -> None:
    import signal
    import sys
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Run migrations on startup (idempotent)
    runner.migrate()

    host = config.gateway_bind_host()
    port = config.gateway_bind_port()

    # Try to start Slack
    try:
        from slack_sdk import WebClient
        import keyring
        bot_token = keyring.get_password("interceder", "slack_bot_token")
        if not bot_token:
            bot_token = os.environ.get("INTERCEDER_SLACK_BOT_TOKEN")
        slack_web_client = WebClient(token=bot_token) if bot_token else None
    except Exception:
        slack_web_client = None

    slack_thread, slack_handler = _start_slack_socket_mode(slack_web_client)

    log.info("starting gateway on %s:%d", host, port)
    uv_config = uvicorn.Config(
        build_app(slack_client=slack_web_client),
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

    if slack_handler:
        try:
            slack_handler.close()
        except Exception:
            pass
    log.info("gateway shut down cleanly")
    sys.exit(0)
