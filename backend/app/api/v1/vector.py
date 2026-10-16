from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, require_role
from app.auth.rbac import Role
from app.embeddings.vector_store import VectorStoreManager
from app.schemas.common_schema import VectorSearchRequest, VectorSearchResult

router = APIRouter(prefix="/vector", tags=["Vector Search"])


@router.post("/search", response_model=list[VectorSearchResult])
def search(payload: VectorSearchRequest, _: CurrentUser = Depends(require_role(Role.VIEWER))):
    """Direct vector similarity search over indexed schema documentation —
    mainly useful for debugging retrieval quality."""
    store = VectorStoreManager()
    results = store.similarity_search(payload.query, k=payload.top_k)
    return [VectorSearchResult(content=doc.page_content, metadata=doc.metadata, score=score) for doc, score in results]
