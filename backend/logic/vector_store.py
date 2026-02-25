import numpy as np
from numpy.typing import NDArray
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from ..core.logging_config import get_logger
from ..core.config import settings
from .embedding_service import create_embedding_service, EmbeddingService

logger = get_logger(__name__)


@dataclass
class ThreatRecord:
    """Record of a threat stored in vector memory."""

    domain: str
    risk_score: str
    category: str
    summary: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "risk_score": self.risk_score,
            "category": self.category,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreatRecord":
        """Create from dictionary."""
        return cls(
            domain=data["domain"],
            risk_score=data["risk_score"],
            category=data["category"],
            summary=data["summary"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class ThreatMatch:
    """A threat match with similarity score."""

    record: ThreatRecord
    similarity: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **self.record.to_dict(),
            "similarity": self.similarity,
        }


class VectorMemory:
    """RAG system using real embeddings for threat memory.

    Supports multiple embedding providers:
    - sentence-transformers (default, local/offline)
    - gemini (cloud, requires API key)
    - mock (for testing)
    """

    def __init__(
        self,
        embedding_provider: str = "sentence-transformers",
        embedding_service: Optional[EmbeddingService] = None,
        index_path: Optional[str] = None,
        similarity_threshold: float = 0.7,
    ):
        """Initialize VectorMemory.

        Args:
            embedding_provider: Provider name ("sentence-transformers", "gemini", "mock")
            embedding_service: Optional pre-configured embedding service (for testing)
            index_path: Path for persistence (optional)
            similarity_threshold: Minimum similarity for matches
        """
        self._embeddings: List[NDArray[np.float32]] = []
        self._metadata: List[ThreatRecord] = []
        self._embedding_service: Optional[EmbeddingService] = None
        self._dimension: int = 0
        self._available: bool = False
        self._index_path: Optional[Path] = Path(index_path) if index_path else None
        self._similarity_threshold: float = similarity_threshold

        # Use provided embedding service or create one
        if embedding_service is not None:
            self._embedding_service = embedding_service
            if self._embedding_service.is_available():
                self._dimension = self._embedding_service.get_dimension()
                self._available = True
            logger.info(
                "VectorMemory initialized with provided service",
                extra={"dimension": self._dimension, "available": self._available},
            )
        else:
            try:
                self._embedding_service = create_embedding_service(
                    provider=embedding_provider,
                    model="all-MiniLM-L6-v2",
                    api_key=settings.GEMINI_API_KEY,
                )

                if self._embedding_service.is_available():
                    self._dimension = self._embedding_service.get_dimension()
                    self._available = True
                    logger.info(
                        "VectorMemory initialized",
                        extra={
                            "provider": embedding_provider,
                            "dimension": self._dimension,
                        },
                    )
                else:
                    logger.warning("Embedding service not available")
                    self._embedding_service = None

            except Exception as e:
                logger.error(f"Failed to initialize embedding service: {e}")
                self._embedding_service = None

        # Load existing data if index_path exists
        if self._index_path:
            self._load_from_disk()

    def add_to_memory(
        self,
        text: str,
        metadata: Dict[str, Any],
        persist: bool = False,
    ) -> bool:
        """Generate embedding and store in memory.

        Args:
            text: The text to embed (e.g., domain name, threat summary)
            metadata: Associated metadata (domain, category, risk_score, etc.)
            persist: Whether to persist to disk

        Returns:
            True if successfully added, False otherwise
        """
        if not self._available or self._embedding_service is None:
            logger.warning("Embedding service not available, cannot add to memory")
            return False

        try:
            # Generate real embedding using the embedding service
            embedding = self._embedding_service.embed(text)

            self._embeddings.append(embedding)

            # Create ThreatRecord from metadata
            record = ThreatRecord(
                domain=metadata.get("domain", text),
                risk_score=metadata.get("risk_score", "Unknown"),
                category=metadata.get("category", "Unknown"),
                summary=metadata.get("summary", ""),
                timestamp=metadata.get("timestamp", ""),
                metadata=metadata,
            )
            self._metadata.append(record)

            logger.info(
                "Added embedding to memory",
                extra={
                    "text_preview": text[:50] + "..." if len(text) > 50 else text,
                    "total_embeddings": len(self._embeddings),
                    "dimension": len(embedding),
                },
            )

            if persist and self._index_path:
                self._save_to_disk()

            return True

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return False

    def query_memory(self, text: str, k: int = 3) -> List[Dict[str, Any]]:
        """Find top-k similar past threats using cosine similarity.

        Args:
            text: The query text to search for
            k: Number of top results to return

        Returns:
            List of metadata dicts for the most similar stored items
        """
        if len(self._embeddings) == 0:
            return []

        if not self._available or self._embedding_service is None:
            logger.warning("Embedding service not available, cannot query memory")
            return []

        try:
            # Generate query embedding using the embedding service
            query_embedding = self._embedding_service.embed(text)

            # Calculate cosine similarity with all stored embeddings
            similarities: List[tuple[float, int]] = []
            for i, embedding in enumerate(self._embeddings):
                # Handle potential dimension mismatch
                if len(query_embedding) != len(embedding):
                    logger.warning(
                        f"Dimension mismatch: query={len(query_embedding)}, stored={len(embedding)}"
                    )
                    continue

                # Calculate cosine similarity
                dot_product = float(np.dot(query_embedding, embedding))
                norm_query = float(np.linalg.norm(query_embedding))
                norm_embedding = float(np.linalg.norm(embedding))

                if norm_query == 0 or norm_embedding == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (norm_query * norm_embedding)

                similarities.append((similarity, i))

            # Sort by similarity (descending) and return top-k
            similarities.sort(reverse=True, key=lambda x: x[0])
            top_indices = [idx for _, idx in similarities[:k]]

            # Return corresponding metadata with similarity scores
            results = []
            for idx in top_indices:
                result = self._metadata[idx].to_dict()
                result["_similarity_score"] = similarities[top_indices.index(idx)][0]
                results.append(result)

            logger.info(
                "Query completed",
                extra={
                    "query_preview": text[:50] + "..." if len(text) > 50 else text,
                    "results_found": len(results),
                    "top_score": similarities[0][0] if similarities else 0,
                },
            )
            return results

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def find_similar_threats(
        self,
        text: str,
        k: int = 5,
        min_similarity: Optional[float] = None,
    ) -> List[ThreatMatch]:
        """Find similar threats and return as ThreatMatch objects.

        Args:
            text: The query text
            k: Max number of results
            min_similarity: Minimum similarity threshold (uses class default if None)

        Returns:
            List of ThreatMatch objects
        """
        if min_similarity is None:
            min_similarity = self._similarity_threshold

        results = self.query_memory(text, k=k)
        matches = []
        for result in results:
            score = result.pop("_similarity_score", 0)
            if score >= min_similarity:
                record = ThreatRecord.from_dict(result)
                matches.append(ThreatMatch(record=record, similarity=score))

        return matches

    def get_threat_cluster(
        self,
        text: str,
        min_similarity: float = 0.7,
    ) -> List[ThreatMatch]:
        """Get all threats above similarity threshold.

        Args:
            text: The query text
            min_similarity: Minimum similarity for cluster membership

        Returns:
            List of ThreatMatch objects in the cluster
        """
        return self.find_similar_threats(text, k=100, min_similarity=min_similarity)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector memory."""
        return {
            "total_embeddings": len(self._embeddings),
            "dimension": self._dimension,
            "similarity_threshold": self._similarity_threshold,
            "is_available": self._available,
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector memory (alias for get_stats)."""
        return {
            "total_embeddings": len(self._embeddings),
            "total_metadata": len(self._metadata),
            "embedding_dimensions": self._dimension,
            "memory_enabled": self._available,
        }

    def clear_memory(self) -> None:
        """Clear all stored embeddings and metadata."""
        self._embeddings = []
        self._metadata = []
        logger.info("Cleared all stored embeddings")

    def _save_to_disk(self) -> None:
        """Save metadata to disk."""
        if not self._index_path:
            return

        self._index_path.mkdir(parents=True, exist_ok=True)
        metadata_path = self._index_path / "metadata.json"

        data = {
            "dimension": self._dimension,
            "records": [record.to_dict() for record in self._metadata],
        }

        with open(metadata_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self._metadata)} records to disk")

    def _load_from_disk(self) -> None:
        """Load metadata from disk."""
        if not self._index_path:
            return

        metadata_path = self._index_path / "metadata.json"
        if not metadata_path.exists():
            return

        try:
            with open(metadata_path) as f:
                data = json.load(f)

            self._metadata = [ThreatRecord.from_dict(r) for r in data.get("records", [])]

            # Re-generate embeddings for loaded metadata
            if self._available and self._embedding_service:
                for record in self._metadata:
                    embedding = self._embedding_service.embed(record.domain)
                    self._embeddings.append(embedding)

            logger.info(f"Loaded {len(self._metadata)} records from disk")

        except Exception as e:
            logger.error(f"Failed to load from disk: {e}")

    # Backward compatibility properties
    @property
    def embeddings(self) -> List[NDArray[np.float32]]:
        """Backward compatibility alias for _embeddings."""
        return self._embeddings

    @property
    def metadata(self) -> List[Dict[str, Any]]:
        """Return metadata as list of dicts for backward compatibility."""
        return [record.to_dict() for record in self._metadata]


# Global instance for singleton pattern
vector_memory = VectorMemory()