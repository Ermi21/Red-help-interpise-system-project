from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db_session, require_role
from app.auth.rbac import Role
from app.notifications.notifier import dispatch_alert
from app.repositories.alert_repository import AlertRepository
from app.schemas.health_schema import AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(db: Session = Depends(get_db_session), _: CurrentUser = Depends(require_role(Role.VIEWER))):
    return AlertRepository(db).list_recent()


@router.post("/test", response_model=dict)
def send_test_alert(_: CurrentUser = Depends(require_role(Role.ADMIN))):
    """Fires a low-stakes test notification through every enabled channel
    so an admin can verify configuration without waiting for a real issue."""
    channels = dispatch_alert(
        title="Test alert",
        severity="critical",  # forced to critical so it clears the notify threshold regardless of config
        description="This is a test notification triggered manually from the admin API.",
        recommendation="No action needed — this confirms notification channels are working.",
        category="test",
    )
    return {"dispatched_to": channels}
