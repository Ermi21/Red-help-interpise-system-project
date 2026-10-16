from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.metadata import TableMetadata
from app.repositories.base_repository import BaseRepository


class MetadataRepository(BaseRepository[TableMetadata]):
    def __init__(self, session: Session):
        super().__init__(session, TableMetadata)

    def get_by_table_name(self, table_name: str) -> TableMetadata | None:
        stmt = select(TableMetadata).where(TableMetadata.table_name == table_name)
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert(self, table_name: str, schema_name: str | None, is_view: bool, raw_schema: dict, description: str) -> TableMetadata:
        existing = self.get_by_table_name(table_name)
        if existing:
            existing.schema_name = schema_name
            existing.is_view = is_view
            existing.raw_schema_json = raw_schema
            existing.ai_generated_description = description
            existing.last_refreshed_at = datetime.utcnow()
            self.session.flush()
            return existing

        record = TableMetadata(
            table_name=table_name,
            schema_name=schema_name,
            is_view=is_view,
            raw_schema_json=raw_schema,
            ai_generated_description=description,
        )
        return self.add(record)

    def list_all(self) -> list[TableMetadata]:
        return list(self.session.execute(select(TableMetadata)).scalars().all())
