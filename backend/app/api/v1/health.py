from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db_session, require_role
from app.auth.rbac import Role
from app.schemas.health_schema import HealthReportResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["Database Health"])


@router.post("/analyze", response_model=HealthReportResponse)
def analyze(db: Session = Depends(get_db_session), _: CurrentUser = Depends(require_role(Role.ANALYST))):
    """Runs a fresh health analysis and dispatches notifications for any
    high/critical issues found. Read-only against the target database."""
    return HealthService(db).run_analysis(notify=True)


@router.get("/report", response_model=HealthReportResponse)
def latest_report(db: Session = Depends(get_db_session), _: CurrentUser = Depends(require_role(Role.VIEWER))):
    """Convenience alias that runs analysis without triggering
    notifications, for dashboards that poll frequently."""
    return HealthService(db).run_analysis(notify=False)
