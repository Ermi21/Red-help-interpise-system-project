"""
Ties together health analysis (app.monitoring.health_analyzer), alert
persistence, and notification dispatch — the "Database Health Analysis" +
"System Administrator Notification" features (spec sections 4 & 7).
"""
from sqlalchemy.orm import Session

from app.database.connection import get_target_engine
from app.monitoring.health_analyzer import analyze_health
from app.models.alert import Alert
from app.notifications.notifier import dispatch_alert
from app.repositories.alert_repository import AlertRepository
from app.schemas.health_schema import HealthIssue, HealthReportResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

from app.config.settings import get_settings

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class HealthService:
    def __init__(self, app_session: Session):
        self.alert_repo = AlertRepository(app_session)

    def run_analysis(self, notify: bool = True) -> HealthReportResponse:
        engine = get_target_engine()
        report = analyze_health(engine)
        settings = get_settings()
        min_level = _SEVERITY_ORDER.get((settings.notify_min_severity or "medium").lower(), 2)

        for issue in report["issues"]:
            severity = issue.get("severity", "medium").lower()
            issue_level = _SEVERITY_ORDER.get(severity, 2)
            should_notify = notify and (issue_level >= min_level)

            channels = {}
            if should_notify:
                try:
                    channels = dispatch_alert(
                        title=f"{issue['category']}: {issue['table'] or 'database'}",
                        severity=issue["severity"],
                        description=issue["description"],
                        recommendation=issue["recommendation"],
                        category=issue["category"],
                    )
                except Exception as exc:
                    logger.warning("Alert dispatch notification channel error: %s", exc)

            alert = Alert(
                severity=issue["severity"],
                category=issue["category"],
                title=f"{issue['category']}: {issue['table'] or 'database'}",
                description=issue["description"],
                recommended_action=issue["recommendation"],
                context_json={"table": issue["table"], "column": issue["column"]},
                notified=bool(channels),
                notified_channels=channels,
            )
            self.alert_repo.add(alert)

        return HealthReportResponse(
            generated_at=report["generated_at"],
            tables_analyzed=report["tables_analyzed"],
            issues=[HealthIssue(**i) for i in report["issues"]],
        )
