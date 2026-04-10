"""FastAPI app factory for the Gateway service.

Phase 1: Slack Socket Mode integration + outbox drain background task.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from interceder import config
from interceder.memory import db

log = logging.getLogger("interceder.gateway.app")


def build_app(*, slack_client: object | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Open a shared DB connection for queue operations
        conn = db.connect(config.db_path())
        app.state.db_conn = conn
        app.state.slack_client = slack_client

        # Start background outbox drain
        drain_task = asyncio.create_task(_outbox_drain_loop(app))

        yield

        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass
        conn.close()

    app = FastAPI(title="Interceder Gateway", version="0.0.1", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "gateway"}

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        return (
            "<!doctype html><html><head><title>Interceder</title></head>"
            "<body><h1>Interceder Gateway</h1>"
            "<p>Phase 1 — Slack connected.</p>"
            "</body></html>"
        )

    from interceder.gateway.ws import ws_endpoint

    @app.websocket("/ws")
    async def websocket_handler(websocket: WebSocket) -> None:
        await ws_endpoint(websocket)

    from interceder.gateway.api import router as api_router
    app.include_router(api_router)

    return app


async def _outbox_drain_loop(app: FastAPI) -> None:
    """Background task: drain outbox every 0.5s."""
    from interceder.gateway.outbox_drain import drain_and_send

    while True:
        try:
            conn = app.state.db_conn
            slack_client = app.state.slack_client
            if conn and slack_client:
                drain_and_send(conn, slack_client=slack_client)
        except Exception:
            log.exception("outbox drain error")
        await asyncio.sleep(0.5)
