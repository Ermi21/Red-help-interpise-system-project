"""
WebSocket endpoint — /api/v1/ws/notifications

Authenticated clients receive real-time events from the event bus.
The token is passed as a query-parameter (?token=...) because browsers
cannot set Authorization headers on WebSocket connections.

On disconnect or error the subscription is automatically cleaned up.
The client should reconnect with exponential backoff if the socket closes.
"""
import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.auth.jwt_handler import decode_access_token
from app.core.event_bus import subscribe, unsubscribe
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket event stream.

    1. Validate JWT.
    2. Send a "connected" confirmation.
    3. Forward every event from the bus to this client.
    4. Clean up on disconnect.
    """
    # ── Authenticate ──────────────────────────────────────────────────────────
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub", "unknown")
        role    = payload.get("role", "viewer")
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    await websocket.accept()
    logger.info("WS connected: user=%s role=%s", user_id, role)

    # ── Subscribe to event bus ─────────────────────────────────────────────────
    queue = await subscribe()

    # Send a handshake so the client knows it is live
    await websocket.send_json({
        "type": "connected",
        "user_id": user_id,
        "role": role,
        "message": "Real-time event stream active",
    })

    try:
        while True:
            # Wait for the next event (timeout every 25 s to send a keepalive)
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25)
            except asyncio.TimeoutError:
                # Send a ping so the browser doesn't close an idle socket
                await websocket.send_json({"type": "ping"})
                continue

            # Role-based filtering: viewers don't see security internals
            if role == "viewer" and event.get("source") == "security":
                continue

            await websocket.send_json({"type": "event", "data": event})

    except WebSocketDisconnect:
        logger.info("WS disconnected: user=%s", user_id)
    except Exception as exc:
        logger.warning("WS error for user=%s: %s", user_id, exc)
    finally:
        await unsubscribe(queue)
