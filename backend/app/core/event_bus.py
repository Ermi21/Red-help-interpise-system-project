"""
In-process async event bus — no Redis required.

Usage
-----
# publish an event (from anywhere in the codebase):
from app.core.event_bus import publish_event
await publish_event(
    source="server",
    event_type="cpu_high",
    severity="warning",
    title="CPU usage above 85%",
    message="CPU at 91% for the past 15 s",
    metadata={"cpu_percent": 91.0},
)

# subscribe (from the WebSocket handler):
from app.core.event_bus import subscribe, unsubscribe
queue = await subscribe()
try:
    event = await asyncio.wait_for(queue.get(), timeout=30)
finally:
    await unsubscribe(queue)

Architecture
------------
- A single module-level asyncio.Queue per connected WebSocket client.
- publish_event() puts the event into EVERY subscriber queue (fan-out).
- Events are also persisted to the `notifications` table via a background
  task so they survive a page reload.
- Maximum 500 events kept in-flight; oldest are dropped if a slow client
  falls behind (prevents memory growth).
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

# All active subscriber queues  {queue_id: asyncio.Queue}
_subscribers: dict[str, asyncio.Queue] = {}
_MAX_QUEUE_SIZE = 500


async def subscribe() -> asyncio.Queue:
    """Register a new subscriber.  Returns the queue to read events from."""
    q: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
    q_id = str(uuid.uuid4())
    _subscribers[q_id] = q
    # Store the id on the queue so unsubscribe can find it by identity
    q._bus_id = q_id  # type: ignore[attr-defined]
    logger.debug("Event bus: subscriber %s connected (%d total)", q_id, len(_subscribers))
    return q


async def unsubscribe(q: asyncio.Queue) -> None:
    """Remove a subscriber queue (call on WebSocket disconnect)."""
    q_id = getattr(q, "_bus_id", None)
    if q_id and q_id in _subscribers:
        del _subscribers[q_id]
        logger.debug("Event bus: subscriber %s disconnected (%d total)", q_id, len(_subscribers))


def _build_event(
    source: str,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    metadata: dict[str, Any] | None,
    user_id: str | None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "source": source,
        "event_type": event_type,
        "severity": severity,
        "title": title,
        "message": message,
        "metadata": metadata or {},
        "user_id": user_id,
        "status": "new",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def publish_event(
    source: str,
    event_type: str,
    severity: str,
    title: str,
    message: str = "",
    metadata: dict[str, Any] | None = None,
    user_id: str | None = None,
    persist: bool = True,
) -> dict:
    """
    Publish an event to all connected WebSocket clients AND persist it to
    the `notifications` table.

    Parameters
    ----------
    source      : "database" | "server" | "security" | "system"
    event_type  : fine-grained type, e.g. "cpu_high", "login_failed"
    severity    : "info" | "warning" | "critical"
    title       : short human-readable title (shown in the bell badge)
    message     : longer description
    metadata    : arbitrary JSON dict
    user_id     : user who triggered the event (optional)
    persist     : write to the notifications table (default True)
    """
    event = _build_event(source, event_type, severity, title, message, metadata, user_id)

    # Fan-out to all connected subscribers
    dead: list[str] = []
    for q_id, q in list(_subscribers.items()):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            # Slow client — drop oldest, push newest
            try:
                q.get_nowait()
                q.put_nowait(event)
            except Exception:
                dead.append(q_id)

    for q_id in dead:
        _subscribers.pop(q_id, None)

    # Persist to the DB in a background task so we never block the caller
    if persist:
        asyncio.ensure_future(_persist_event(event))

    logger.debug(
        "Event bus: published %s/%s (%s) to %d subscribers",
        source, event_type, severity, len(_subscribers),
    )
    return event


def _do_persist_event(event: dict) -> None:
    try:
        from datetime import datetime
        from app.database.connection import app_session
        from app.models.notification import Notification

        occurred = datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
        with app_session() as session:
            session.add(Notification(
                id=event["id"],
                source=event["source"],
                event_type=event["event_type"],
                severity=event["severity"],
                title=event["title"],
                message=event["message"],
                metadata_json=event.get("metadata", {}),
                user_id=event.get("user_id"),
                status="new",
                occurred_at=occurred,
            ))
    except Exception as exc:
        logger.warning("Event bus: failed to persist event: %s", exc)


_persist_semaphore = asyncio.Semaphore(5)


async def _persist_event(event: dict) -> None:
    """Write the event to the notifications table in a background thread with concurrency limit."""
    try:
        async with _persist_semaphore:
            await asyncio.to_thread(_do_persist_event, event)
    except Exception as exc:
        logger.warning("Event bus: failed during background persist: %s", exc)



def publish_event_sync(
    source: str,
    event_type: str,
    severity: str,
    title: str,
    message: str = "",
    metadata: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    """
    Synchronous wrapper — safe to call from non-async code (background
    threads, middleware).  Tries to schedule on the running event loop;
    falls back to direct DB write if no loop is running.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(publish_event(
                source=source, event_type=event_type, severity=severity,
                title=title, message=message, metadata=metadata, user_id=user_id,
            ))
        else:
            # No running loop — persist directly (synchronous)
            _persist_event_sync(source, event_type, severity, title, message, metadata, user_id)
    except Exception as exc:
        logger.warning("publish_event_sync failed: %s", exc)


def _persist_event_sync(
    source: str, event_type: str, severity: str,
    title: str, message: str, metadata: dict | None, user_id: str | None,
) -> None:
    """Direct synchronous DB write, used when there is no running event loop."""
    try:
        import uuid as _uuid
        from datetime import datetime, timezone
        from app.database.connection import app_session
        from app.models.notification import Notification

        now = datetime.now(timezone.utc)
        with app_session() as session:
            session.add(Notification(
                id=str(_uuid.uuid4()),
                source=source,
                event_type=event_type,
                severity=severity,
                title=title,
                message=message,
                metadata_json=metadata or {},
                user_id=user_id,
                status="new",
                occurred_at=now,
            ))
    except Exception as exc:
        logger.warning("_persist_event_sync failed: %s", exc)
