"""Embedding function with resilient local fallback."""
from functools import lru_cache
import hashlib
from typing import List

from langchain_core.embeddings import Embeddings
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResilientEmbeddings(Embeddings):
    """Wrapper that tries OllamaEmbeddings, and falls back to deterministic vectors if Ollama is offline."""
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url
        self._ollama = None

    def _get_ollama(self):
        if self._ollama is None:
            try:
                from langchain_ollama import OllamaEmbeddings
                # Use a short timeout so that when Ollama is offline the first
                # attempt fails quickly (< 2 s) instead of hanging for the OS
                # default TCP timeout (often 30 s+).
                self._ollama = OllamaEmbeddings(
                    model=self.model,
                    base_url=self.base_url,
                    timeout=2,
                )
            except Exception as e:
                logger.warning("Could not initialize OllamaEmbeddings: %s", e)
        return self._ollama

    def _fallback_vector(self, text: str) -> List[float]:
        # Generate stable 384-dim pseudo-vector from text tokens and sha256
        h = hashlib.sha256(text.encode("utf-8")).digest()
        raw = (h * 12)[:384]
        return [((b / 127.5) - 1.0) for b in raw]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        ollama = self._get_ollama()
        if ollama:
            try:
                return ollama.embed_documents(texts)
            except Exception as e:
                logger.warning("Ollama embed_documents bypassed: %s", e)
        return [self._fallback_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        ollama = self._get_ollama()
        if ollama:
            try:
                return ollama.embed_query(text)
            except Exception as e:
                logger.warning("Ollama embed_query bypassed: %s", e)
        return self._fallback_vector(text)


@lru_cache
def get_embedding_function() -> Embeddings:
    settings = get_settings()
    return ResilientEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )
