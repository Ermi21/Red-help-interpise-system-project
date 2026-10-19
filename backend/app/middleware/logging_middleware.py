import time
import uuid

from app.monitoring.error_detector import record_error_event
from app.utils.logger import get_logger

logger = get_logger("app.request")


class RequestLoggingMiddleware:
    """Pure ASGI middleware for logging requests without BaseHTTPMiddleware deadlocks."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            method = scope.get("method", "GET")
            path = scope.get("path", "")
            client = scope.get("client", [None])[0] if scope.get("client") else None

            logger.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client": client,
                },
            )

            # Feed the metrics collector's in-process request counter
            try:
                from app.workers.metrics_collector import record_request
                record_request(status_code, duration_ms)
            except Exception:
                pass

            if status_code >= 500:
                record_error_event(
                    category="api",
                    message=f"{method} {path} returned {status_code}",
                    severity="high",
                    context={"request_id": request_id},
                )

                # Also publish to the real-time event bus
                try:
                    from app.core.event_bus import publish_event_sync
                    publish_event_sync(
                        source="server",
                        event_type="api_error",
                        severity="warning",
                        title=f"API error {status_code}: {method} {path}",
                        message=f"Request {request_id} returned HTTP {status_code} in {duration_ms:.0f} ms.",
                        metadata={
                            "method": method,
                            "path": path,
                            "status_code": status_code,
                            "duration_ms": duration_ms,
                        },
                    )
                except Exception:
                    pass

