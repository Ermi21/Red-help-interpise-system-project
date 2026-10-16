from fastapi import APIRouter

from app.api.v1 import alerts, auth, chat, health, logs, monitoring, recommendations, schema, vector

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(schema.router)
api_router.include_router(health.router)
api_router.include_router(recommendations.router)
api_router.include_router(alerts.router)
api_router.include_router(logs.router)
api_router.include_router(vector.router)
api_router.include_router(monitoring.router)
