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
