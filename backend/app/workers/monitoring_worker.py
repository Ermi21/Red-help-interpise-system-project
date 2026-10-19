"""
Background worker that continuously collects monitoring metrics
and broadcasts them via WebSocket to all connected clients.

Replaces the need for frontend HTTP polling.
"""
import asyncio
from datetime import datetime

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def monitoring_worker():
    """
    Continuously collect monitoring metrics and broadcast via WebSocket.
    Runs in background as long as the application is running.
    """
    settings = get_settings()
    
    if not settings.websocket_enabled:
        logger.info("WebSocket monitoring worker disabled (WEBSOCKET_ENABLED=false)")
        return
    
    interval = settings.websocket_monitoring_interval_s
    logger.info(f"Starting WebSocket monitoring worker (interval={interval}s)")
    
    # Import here to avoid circular dependency
    from app.websocket.server import (
        emit_database_update,
        emit_server_update,
        emit_security_update,
        emit_notifications_update,
    )
    
    # Import monitoring endpoints (bypass auth for worker)
    from app.api.v1.monitoring import (
        get_database_metrics,
        get_server_metrics,
        get_security_events,
        get_notifications,
    )
    
    # Mock user for internal calls (bypass dependency injection)
    class MockUser:
        def __init__(self):
            self.id = "system"
            self.username = "monitoring_worker"
            self.role = "admin"
    
    mock_user = MockUser()
    
    while True:
        try:
            # Collect all metrics in background threads so the event loop remains fast
            db_metrics = await asyncio.to_thread(get_database_metrics, mock_user)
            srv_metrics = await asyncio.to_thread(get_server_metrics, mock_user)
            sec_events = await asyncio.to_thread(get_security_events, mock_user)
            notifications = await asyncio.to_thread(get_notifications, mock_user)
            
            # Broadcast to all subscribed WebSocket clients
            await emit_database_update(db_metrics)
            await emit_server_update(srv_metrics)
            await emit_security_update(sec_events)
            await emit_notifications_update(notifications)
            
            logger.debug(f"Monitoring broadcast complete at {datetime.utcnow().strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Monitoring worker error: {e}")
        
        # Wait for next interval
        await asyncio.sleep(interval)


async def run_monitoring_worker():
    """Entry point for starting the monitoring worker."""
    try:
        await monitoring_worker()
    except asyncio.CancelledError:
        logger.info("Monitoring worker cancelled")
    except Exception as e:
        logger.error(f"Monitoring worker crashed: {e}")
