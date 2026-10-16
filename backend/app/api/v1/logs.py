from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, require_role
from app.auth.rbac import Role
from app.monitoring.error_detector import build_error_report

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("")
def get_logs(limit: int = 100, _: CurrentUser = Depends(require_role(Role.ANALYST))):
    return build_error_report(limit=limit)
