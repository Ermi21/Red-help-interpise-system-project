"""
ChromaDB-backed vector store for the Enterprise 3-System RAG Intelligence Platform.

Manages vector embeddings and semantic search across:
  1. Database System: Schema documentation, table definitions, connection pooler architecture, and indexing runbooks.
  2. Server & Infrastructure System: Host compute topology, CPU/RAM/Disk metrics, Docker cluster services, and SRE runbooks.
  3. Security System: Zero-Trust WAF policies, 247 firewall rules, brute-force defense, and incident response guides.

This store holds ONLY system metadata, operational runbooks, and architectural knowledge
— never raw customer records — ensuring zero risk of sensitive row data leakage.
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from functools import lru_cache
from typing import List, Tuple, Optional

import chromadb.config
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.config.settings import get_settings
from app.embeddings.embedder import get_embedding_function
from app.utils.exceptions import VectorStoreError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SEEDED_MEMORY_FALLBACK = False


@lru_cache
def get_vector_store() -> Chroma:
    settings = get_settings()
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embedding_function(),
        persist_directory=settings.chroma_persist_dir,
        client_settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


class VectorStoreManager:
    def __init__(self):
        self.store = get_vector_store()

    def add_documents(self, documents: list[Document]) -> int:
        if not documents:
            return 0
        try:
            ids = [
                f"{doc.metadata.get('system', 'sys')}-{doc.metadata.get('category', 'cat')}-{i}-{abs(hash(doc.page_content)) % 10000000}"
                for i, doc in enumerate(documents)
            ]
            self.store.add_documents(documents, ids=ids)
            return len(documents)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to add documents to vector store: %s", exc)
            raise VectorStoreError("Failed to index documents.") from exc

    def count(self) -> int:
        """Return total number of vectors in the collection."""
        try:
            collection = getattr(self.store, "_collection", None)
            if collection:
                return collection.count()
        except Exception:
            pass
        return 0

    def similarity_search(self, query: str, k: int = 5, filter_: dict | None = None) -> list[tuple[Document, float]]:
        """Search vector store and return (Document, score) tuples."""
        try:
            return self.store.similarity_search_with_relevance_scores(query, k=k, filter=filter_)
        except Exception as exc:
            logger.debug("similarity_search_with_relevance_scores fallback to similarity_search: %s", exc)
            try:
                docs = self.store.similarity_search(query, k=k, filter=filter_)
                return [(d, 0.85) for d in docs]
            except Exception as e2:
                logger.warning("Vector similarity search failed: %s", e2)
                return []

    def similarity_search_3systems(
        self,
        query: str,
        k: int = 5,
        system: Optional[str] = None,
    ) -> list[tuple[Document, float]]:
        """
        Unified multi-system vector retrieval:
        - If system is 'database', 'server', or 'security', filters or boosts by that domain.
        - If system is 'all' or None, retrieves across the entire 3-system knowledge base.
        - Falls back gracefully to in-memory keyword matching if vector store returns empty.
        """
        results: list[tuple[Document, float]] = []
        sys_clean = (system or "").lower().strip()
        if sys_clean in ("infrastructure", "sre", "host"):
            sys_clean = "server"
        elif sys_clean in ("cyber", "defense", "waf"):
            sys_clean = "security"

        # 1. Attempt Chroma vector search with domain filter if specified
        if sys_clean and sys_clean in ("database", "server", "security"):
            try:
                results = self.similarity_search(query, k=k, filter_={"system": sys_clean})
            except Exception as e:
                logger.debug("Filtered vector search failed, trying unfiltered: %s", e)

        # 2. If filtered search had no hits or system='all', run full search
        if not results:
            try:
                results = self.similarity_search(query, k=k)
            except Exception as e:
                logger.warning("General vector search failed: %s", e)

        # 3. Resilient In-Memory Fallback: If Chroma returns empty, match against knowledge corpus
        if not results:
            from app.embeddings.chunking import get_3systems_knowledge_corpus
            corpus = get_3systems_knowledge_corpus()
            q_words = [w.lower() for w in query.split() if len(w) > 3]

            scored_matches = []
            for text_chunk, meta in corpus:
                # Check domain compatibility
                if sys_clean and sys_clean not in ("all", ""):
                    chunk_sys = meta.get("system", "")
                    if chunk_sys != sys_clean and chunk_sys != "all":
                        continue

                # Compute keyword overlap score
                content_lower = text_chunk.lower()
                title_lower = meta.get("title", "").lower()
                keywords_lower = meta.get("keywords", "").lower()

                match_count = sum(
                    1.5 if w in title_lower else (1.2 if w in keywords_lower else (1.0 if w in content_lower else 0))
                    for w in q_words
                )

                if match_count > 0 or not q_words:
                    score = min(0.95, 0.5 + (match_count * 0.1))
                    scored_matches.append((Document(page_content=text_chunk, metadata=meta), score))

            scored_matches.sort(key=lambda x: x[1], reverse=True)
            results = scored_matches[:k]

        return results

    def seed_3systems_knowledge(self, force: bool = False) -> int:
        """
        Seeds the Chroma vector store with comprehensive knowledge chunks across
        Database, Server, and Security systems if collection is unseeded or force=True.
        """
        global _SEEDED_MEMORY_FALLBACK
        try:
            current_count = self.count()
            if current_count >= 8 and not force:
                logger.info("Chroma vector store already seeded (%d docs active)", current_count)
                return current_count

            from app.embeddings.chunking import build_3systems_knowledge_docs
            docs = build_3systems_knowledge_docs()
            added = self.add_documents(docs)
            logger.info("Successfully seeded %d multi-system knowledge chunks into ChromaDB", added)
            _SEEDED_MEMORY_FALLBACK = True
            return added
        except Exception as exc:
            logger.warning("ChromaDB vector seeding notice (in-memory fallback active): %s", exc)
            _SEEDED_MEMORY_FALLBACK = True
            return 0

    def delete_by_table(self, table_name: str) -> None:
        """Remove previously indexed chunks for a table before re-indexing it."""
        try:
            self.store.delete(where={"table": table_name})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not clear existing chunks for '%s': %s", table_name, exc)

    def as_retriever(self, k: int = 5):
        return self.store.as_retriever(search_kwargs={"k": k})
