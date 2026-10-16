from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    domain: str | None = "database"


class SourceReference(BaseModel):
    type: str  # "schema_doc" | "query_result"
    label: str
    detail: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    generated_sql: str | None = None
    row_count: int | None = None
    sources: list[SourceReference] = []


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}
