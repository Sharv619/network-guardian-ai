"""
Embedding Service for Vector Store.

This module provides:
- Abstract base class for embedding providers
- SentenceTransformerService for local, offline embeddings
- GeminiEmbeddingService for cloud-based embeddings (fallback)
"""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from numpy.typing import NDArray

from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingService(ABC):
    """Abstract base class for embedding services."""

    @abstractmethod
    def embed(self, text: str) -> NDArray[np.float32]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            A numpy array of floats representing the embedding
        """
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[NDArray[np.float32]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            The number of dimensions in the embedding vector
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the embedding service is available.

        Returns:
            True if the service can generate embeddings
        """
        ...


class SentenceTransformerService(EmbeddingService):

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model: Any = None
        self._dimension: int | None = None
        self._available: bool = False

        try:
            # Add conditional import based on settings availability
            try:
                from backend.core.config import settings
                embedding_enabled = getattr(settings, 'EMBEDDING_SERVICE_ENABLED', True)
                if not embedding_enabled:
                    self._available = False
                    logger.info("SentenceTransformerService disabled via config")
                    return
            except ImportError:
                # If settings aren't available, proceed with default behavior
                pass
            
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            self._available = True
            logger.info(
                "SentenceTransformerService initialized",
                extra={
                    "model": model_name,
                    "dimension": self._dimension,
                },
            )
        except ImportError:
            logger.warning("sentence-transformers not installed, using mock embedding service")
            self._available = False
        except Exception as e:
            logger.error(
                "Failed to initialize SentenceTransformer",
                extra={"model": model_name, "error": str(e)},
            )
            self._available = False

    def embed(self, text: str) -> NDArray[np.float32]:
        """Generate embedding for a single text."""
        if not self._available or self._model is None:
            raise RuntimeError("SentenceTransformerService is not available")

        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)

    def embed_batch(self, texts: list[str]) -> list[NDArray[np.float32]]:
        """Generate embeddings for multiple texts."""
        if not self._available or self._model is None:
            raise RuntimeError("SentenceTransformerService is not available")

        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return [emb.astype(np.float32) for emb in embeddings]

    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is None:
            raise RuntimeError("Model not initialized")
        return self._dimension

    def is_available(self) -> bool:
        """Check if the service is available."""
        return self._available


class GeminiEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str | None = None, model: str = "text-embedding-004"):
        self.model = model
        self._api_key = api_key
        self._client: Any = None
        self._dimension: int = 768
        self._available: bool = False

        try:
            from google import genai

            if api_key:
                self._client = genai.Client(api_key=api_key)
                self._available = True
                logger.info(
                    "GeminiEmbeddingService initialized",
                    extra={"model": model, "dimension": self._dimension},
                )
            else:
                logger.warning("No API key provided for GeminiEmbeddingService")
        except ImportError:
            logger.warning("google-genai not installed")
        except Exception as e:
            logger.error("Failed to initialize GeminiEmbeddingService", extra={"error": str(e)})

    def embed(self, text: str) -> NDArray[np.float32]:
        """Generate embedding using Gemini API."""
        if not self._available or self._client is None:
            raise RuntimeError("GeminiEmbeddingService is not available")

        result = self._client.models.embed_content(
            model=self.model,
            content=text,
        )
        return np.array(result.embedding.values, dtype=np.float32)

    def embed_batch(self, texts: list[str]) -> list[NDArray[np.float32]]:
        """Generate embeddings for multiple texts (sequential API calls)."""
        if not self._available or self._client is None:
            raise RuntimeError("GeminiEmbeddingService is not available")

        embeddings = []
        for text in texts:
            embedding = self.embed(text)
            embeddings.append(embedding)
        return embeddings

    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension

    def is_available(self) -> bool:
        """Check if the service is available."""
        return self._available


class MockEmbeddingService(EmbeddingService):
    """
    Mock embedding service for testing.

    Generates deterministic but meaningless embeddings for testing purposes.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    def embed(self, text: str) -> NDArray[np.float32]:
        """Generate a mock embedding based on text hash."""
        import hashlib

        text_bytes = text.encode("utf-8")
        hash_obj = hashlib.sha256(text_bytes)
        hash_hex = hash_obj.hexdigest()

        embedding = np.array(
            [
                float(int(hash_hex[i % len(hash_hex) : (i % len(hash_hex)) + 2], 16) / 255.0)
                for i in range(self._dimension)
            ],
            dtype=np.float32,
        )

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def embed_batch(self, texts: list[str]) -> list[NDArray[np.float32]]:
        """Generate mock embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension

    def is_available(self) -> bool:
        """Always available for testing."""
        return True


def create_embedding_service(
    provider: str = "sentence-transformers",
    model: str = "all-MiniLM-L6-v2",
    api_key: str | None = None,
) -> EmbeddingService:
    """
    Factory function to create an embedding service.

    Args:
        provider: The embedding provider ("sentence-transformers", "gemini", "mock")
        model: The model name to use
        api_key: API key for cloud providers

    Returns:
        An EmbeddingService instance
    """
    if provider == "sentence-transformers":
        return SentenceTransformerService(model_name=model)
    elif provider == "gemini":
        return GeminiEmbeddingService(api_key=api_key, model=model)
    elif provider == "mock":
        return MockEmbeddingService()
    else:
        logger.warning(
            "Unknown embedding provider, falling back to mock", extra={"provider": provider}
        )
        return MockEmbeddingService()
