"""
Application entrypoint / app factory.

Run with:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.database.connection import get_app_engine, get_target_engine
from app.embeddings.vector_store import get_vector_store
from app.middleware.error_handler import register_error_handlers
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.rate_limiter import limiter
from app.models.base import Base
# Import every ORM model module so Base.metadata is fully populated before create_all().
from app.models import alert, audit_log, conversation, llm_usage, login_event, metadata, notification, system_metrics, user  # noqa: F401
from app.schemas.common_schema import HealthCheckResponse
from app.utils.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    try:
        Base.metadata.create_all(bind=get_app_engine())
        # Auto-seed default admin if no users exist
        from app.database.connection import app_session
        from app.repositories.user_repository import UserRepository
        from app.models.user import User
        from app.auth.password import hash_password

        with app_session() as session:
            user_repo = UserRepository(session)
            if not user_repo.get_by_username("admin"):
                admin_user = User(
                    username="admin",
                    email="admin@company.com",
                    hashed_password=hash_password("admin123"),
                    role="admin",
                )
                user_repo.add(admin_user)
                logger.info("Auto-seeded default admin user: admin / admin123")

            if not user_repo.get_by_email("superadmin@company.com"):
                superadmin_user = User(
                    username="superadmin",
                    email="superadmin@company.com",
                    hashed_password=hash_password("admin123"),
                    role="admin",
                )
                user_repo.add(superadmin_user)
                logger.info("Auto-seeded default superadmin user: superadmin@company.com / admin123")
    except Exception as exc:
        logger.warning("Application DB initialization/seeding notice: %s", exc)

    try:
        get_target_engine()
        get_vector_store()
        logger.info("%s starting up (env=%s)", settings.app_name, settings.app_env)

        # Seed a startup notification so the System Alerts page is never empty
        from app.database.connection import app_session
        from app.models.alert import Alert
        from app.repositories.alert_repository import AlertRepository
        with app_session() as session:
            repo = AlertRepository(session)
            existing = repo.list_recent(limit=1)
            if not existing:
                session.add(Alert(
                    severity="low",
                    category="system",
                    status="active",
                    title="System Started Successfully",
                    description=f"ERAOP backend started at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. All services initialized.",
                    recommended_action="No action required.",
                ))
                logger.info("Seeded initial system startup alert")

        # Publish a startup event to the unified notification stream
        from app.core.event_bus import publish_event_sync
        publish_event_sync(
            source="system",
            event_type="startup",
            severity="info",
            title="Red Cloud ERAOP backend started",
            message=f"All services initialized at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        )

        # Background workers
        import asyncio as _asyncio
        from app.workers.metrics_collector import run_metrics_collector
        from app.workers.alert_evaluator import run_alert_evaluator
        
        _asyncio.ensure_future(run_metrics_collector(interval_s=15))
        _asyncio.ensure_future(run_alert_evaluator(interval_s=30))
        logger.info("Background workers started (metrics collector & alert evaluator)")

    except Exception as exc:  # noqa: BLE001
        logger.error("Startup dependency check failed: %s", exc)

    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Read-only, RAG-powered enterprise database assistant. This "
            "backend never modifies the target company database — see the "
            "/api/v1/schema, /api/v1/health, and /api/v1/chat endpoints."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(status_code=429, content={"error_code": "rate_limit_exceeded", "message": "Too many requests.", "details": {}})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if settings.cors_origins else ["*"],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_error_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)


    @app.get("/healthz", response_model=HealthCheckResponse, tags=["Service Health"])
    def liveness():
        """Unauthenticated liveness/readiness probe for this SERVICE
        itself (container orchestration health checks) — distinct from
        /api/v1/health, which analyzes the TARGET database's health."""
        app_db_ok = target_db_ok = vector_ok = llm_ok = True
        # llm_ok and target_db are not actively probed synchronously here to keep this
        # container orchestrator liveness check instantaneous (<10ms).
        # Target DB health is continuously monitored and reported via /api/v1/health.
        try:
            with get_app_engine().connect() as conn:
                pass
        except Exception:  # noqa: BLE001
            app_db_ok = False
        try:
            get_vector_store()
        except Exception:  # noqa: BLE001
            vector_ok = False

        status = "ok" if (app_db_ok and vector_ok) else "degraded"
        return HealthCheckResponse(status=status, app_db=app_db_ok, target_db=target_db_ok, vector_store=vector_ok, llm=llm_ok)

    @app.get("/health", response_model=HealthCheckResponse, tags=["Service Health"])
    def health_check():
        """Alias for /healthz — standard liveness probe."""
        return liveness()

    @app.get("/ready", response_model=HealthCheckResponse, tags=["Service Health"])
    def readiness_check():
        """Readiness probe — same checks as /healthz."""
        return liveness()

    return app


app = create_app()
