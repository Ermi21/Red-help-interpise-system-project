"""
ChromaDB-backed vector store for schema documentation, table descriptions
and any other knowledge the RAG pipeline should retrieve from.

This store holds ONLY documentation/metadata WE generated about the target
database — never raw customer row data — so there is no risk of sensitive
records leaking into embeddings at rest.
"""
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config.settings import get_settings
from app.embeddings.embedder import get_embedding_function
from app.utils.exceptions import VectorStoreError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def get_vector_store() -> Chroma:
    settings = get_settings()
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embedding_function(),
        persist_directory=settings.chroma_persist_dir,
    )


class VectorStoreManager:
    def __init__(self):
        self.store = get_vector_store()

    def add_documents(self, documents: list[Document]) -> int:
        if not documents:
            return 0
        try:
            ids = [f"{doc.metadata.get('table', 'doc')}-{i}-{hash(doc.page_content) & 0xFFFFFFFF}" for i, doc in enumerate(documents)]
            self.store.add_documents(documents, ids=ids)
            return len(documents)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to add documents to vector store: %s", exc)
            raise VectorStoreError("Failed to index documents.") from exc

    def similarity_search(self, query: str, k: int = 5, filter_: dict | None = None) -> list[tuple[Document, float]]:
        try:
            return self.store.similarity_search_with_relevance_scores(query, k=k, filter=filter_)
        except Exception as exc:  # noqa: BLE001
            logger.error("Vector similarity search failed: %s", exc)
            raise VectorStoreError("Vector search failed.") from exc

    def delete_by_table(self, table_name: str) -> None:
        """Remove all previously indexed chunks for a table before
        re-indexing it (used by schema refresh)."""
        try:
            self.store.delete(where={"table": table_name})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not clear existing chunks for '%s': %s", table_name, exc)

    def as_retriever(self, k: int = 5):
        return self.store.as_retriever(search_kwargs={"k": k})
