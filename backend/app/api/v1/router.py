from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    auth,
    chat,
    health,
    logs,
    monitoring,
    notifications_api,
    recommendations,
    schema,
    security_detail,
    server_detail,
    vector,
    ws,
)

api_router = APIRouter()

# ── Existing routes (unchanged) ───────────────────────────────────────────────
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(schema.router)
api_router.include_router(health.router)
api_router.include_router(recommendations.router)
api_router.include_router(alerts.router)
api_router.include_router(logs.router)
api_router.include_router(vector.router)
api_router.include_router(monitoring.router)

# ── New Phase-1 routes ────────────────────────────────────────────────────────
api_router.include_router(notifications_api.router)   # /notifications
api_router.include_router(server_detail.router)       # /server/*
api_router.include_router(security_detail.router)     # /security/*
api_router.include_router(ws.router)                  # /ws/notifications (WebSocket)
