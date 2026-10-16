from datetime import datetime

from pydantic import BaseModel


class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool
    is_primary_key: bool


class ForeignKeySchema(BaseModel):
    constrained_columns: list[str]
    referred_table: str
    referred_columns: list[str]


class TableSchema(BaseModel):
    name: str
    schema_name: str | None = None
    is_view: bool
    columns: list[ColumnSchema]
    primary_key: list[str]
    foreign_keys: list[ForeignKeySchema]
    ai_description: str | None = None


class HealthIssue(BaseModel):
    category: str
    severity: str
    table: str | None = None
    column: str | None = None
    description: str
    recommendation: str


class HealthReportResponse(BaseModel):
    generated_at: datetime
    tables_analyzed: int
    issues: list[HealthIssue]


class RecommendationResponse(BaseModel):
    issue: str
    severity: str
    recommendation: str
    category: str


class AlertResponse(BaseModel):
    id: str
    severity: str
    category: str
    title: str
    description: str
    recommended_action: str
    status: str = "active"
    notified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
