"""WebSocket endpoint for the webapp.

Handles:
- Incoming user messages (enqueued to inbox)
- Outgoing manager replies (broadcast from outbox drain)
- Ping/pong health checks
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from interceder.gateway.queue import enqueue_inbox
from interceder.schema import Message

log = logging.getLogger("interceder.gateway.ws")

# Track connected websocket clients
_connected_clients: list[WebSocket] = []


async def ws_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket handler for webapp clients."""
    await websocket.accept()
    _connected_clients.append(websocket)
    log.info("webapp client connected (%d total)", len(_connected_clients))

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "message":
                content = data.get("content", "")
                correlation = data.get("correlation_id", f"webapp:{uuid.uuid4().hex[:8]}")
                msg = Message(
                    id=f"webapp-{uuid.uuid4().hex[:12]}",
                    correlation_id=correlation,
                    source="webapp",
                    kind="text",
                    content=content,
                    metadata={"origin": "webapp"},
                    created_at=int(time.time()),
                )
                # Get DB connection from app state
                conn = websocket.app.state.db_conn
                if conn:
                    enqueue_inbox(conn, msg)
                    await websocket.send_json({
                        "type": "ack",
                        "message_id": msg.id,
                    })

    except WebSocketDisconnect:
        pass
    finally:
        _connected_clients.remove(websocket)
        log.info("webapp client disconnected (%d remain)", len(_connected_clients))


async def broadcast_to_webapp(data: dict[str, Any]) -> None:
    """Broadcast a message to all connected webapp clients."""
    disconnected = []
    for ws in _connected_clients:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _connected_clients.remove(ws)
