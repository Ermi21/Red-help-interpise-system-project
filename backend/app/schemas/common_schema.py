from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict = {}


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class VectorSearchResult(BaseModel):
    content: str
    metadata: dict
    score: float | None = None


class HealthCheckResponse(BaseModel):
    status: str
    app_db: bool
    target_db: bool
    vector_store: bool
    llm: bool
