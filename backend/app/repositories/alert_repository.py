from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: Session):
        super().__init__(session, Alert)

    def list_recent(self, limit: int = 100) -> list[Alert]:
        stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def mark_notified(self, alert: Alert, channels: dict) -> Alert:
        alert.notified = True
        alert.notified_channels = channels
        self.session.flush()
        return alert
