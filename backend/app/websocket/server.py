"""
WebSocket server for real-time monitoring updates.
Replaces HTTP polling with persistent connections.
"""
import socketio
from fastapi import FastAPI

from app.auth.jwt_handler import decode_access_token
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create Socket.IO server with ASGI support
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)


@sio.event
async def connect(sid, environ, auth):
    """
    Authenticate WebSocket connection via JWT token.
    Client must provide: { auth: { token: "jwt_token_here" } }
    """
    logger.info(f"WebSocket connection attempt: {sid}")
    
    # Extract token from auth dict
    token = auth.get('token') if auth else None
    
    if not token:
        logger.warning(f"WebSocket connection rejected (no token): {sid}")
        raise socketio.exceptions.ConnectionRefusedError('Authentication required')
    
    try:
        # Verify JWT token
        payload = decode_access_token(token)
        user_id = payload.get('sub')
        username = payload.get('username', 'unknown')
        role = payload.get('role', 'viewer')
        
        # Save session data
        await sio.save_session(sid, {
            'user_id': user_id,
            'username': username,
            'role': role,
        })
        
        logger.info(f"WebSocket authenticated: {sid} (user={username}, role={role})")
        
        # Send confirmation
        await sio.emit('authenticated', {
            'user_id': user_id,
            'username': username,
            'message': 'Connected to EnterpriseHub real-time monitoring'
        }, room=sid)
        
    except Exception as e:
        logger.warning(f"WebSocket authentication failed for {sid}: {e}")
        raise socketio.exceptions.ConnectionRefusedError('Invalid token')


@sio.event
async def disconnect(sid):
    """Handle client disconnect."""
    try:
        session = await sio.get_session(sid)
        username = session.get('username', 'unknown')
        logger.info(f"WebSocket disconnected: {sid} (user={username})")
    except Exception:
        logger.info(f"WebSocket disconnected: {sid}")


@sio.event
async def subscribe(sid, data):
    """
    Subscribe to specific monitoring channels.
    Client sends: { channels: ['database', 'server', 'security', 'notifications'] }
    """
    try:
        session = await sio.get_session(sid)
        username = session.get('username', 'unknown')
        
        channels = data.get('channels', [])
        if not isinstance(channels, list):
            channels = []
        
        # Join Socket.IO rooms for each channel
        for channel in channels:
            if channel in ['database', 'server', 'security', 'notifications', 'alerts']:
                room_name = f'monitoring:{channel}'
                await sio.enter_room(sid, room_name)
                logger.debug(f"User {username} subscribed to {room_name}")
        
        # Confirm subscription
        await sio.emit('subscribed', {
            'channels': channels,
            'message': f'Subscribed to {len(channels)} channel(s)'
        }, room=sid)
        
    except Exception as e:
        logger.error(f"Subscription error for {sid}: {e}")
        await sio.emit('error', {'message': 'Subscription failed'}, room=sid)


@sio.event
async def unsubscribe(sid, data):
    """Unsubscribe from channels."""
    try:
        channels = data.get('channels', [])
        
        for channel in channels:
            room_name = f'monitoring:{channel}'
            await sio.leave_room(sid, room_name)
        
        await sio.emit('unsubscribed', {'channels': channels}, room=sid)
        
    except Exception as e:
        logger.error(f"Unsubscribe error for {sid}: {e}")


@sio.event
async def ping(sid, data):
    """Health check ping-pong."""
    await sio.emit('pong', {'timestamp': data.get('timestamp')}, room=sid)


def get_socketio_app():
    """Get Socket.IO ASGI application for mounting in FastAPI."""
    return socketio.ASGIApp(
        sio,
        socketio_path='socket.io',
    )


# Emitter functions for broadcasting to all subscribers

async def emit_database_update(metrics: dict):
    """Broadcast database metrics to all subscribed clients."""
    try:
        await sio.emit('database_update', metrics, room='monitoring:database')
        logger.debug("Broadcasted database_update to subscribers")
    except Exception as e:
        logger.error(f"Failed to broadcast database_update: {e}")


async def emit_server_update(metrics: dict):
    """Broadcast server metrics to all subscribed clients."""
    try:
        await sio.emit('server_update', metrics, room='monitoring:server')
        logger.debug("Broadcasted server_update to subscribers")
    except Exception as e:
        logger.error(f"Failed to broadcast server_update: {e}")


async def emit_security_update(events: dict):
    """Broadcast security events to all subscribed clients."""
    try:
        await sio.emit('security_update', events, room='monitoring:security')
        logger.debug("Broadcasted security_update to subscribers")
    except Exception as e:
        logger.error(f"Failed to broadcast security_update: {e}")


async def emit_notifications_update(notifications: list):
    """Broadcast notifications to all subscribed clients."""
    try:
        await sio.emit('notifications_update', notifications, room='monitoring:notifications')
        logger.debug("Broadcasted notifications_update to subscribers")
    except Exception as e:
        logger.error(f"Failed to broadcast notifications_update: {e}")


async def emit_alert(alert: dict):
    """Broadcast new alert to all subscribed clients."""
    try:
        await sio.emit('new_alert', alert, room='monitoring:alerts')
        logger.debug(f"Broadcasted new_alert: {alert.get('title', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to broadcast alert: {e}")
