"""
Tests for embedding service and vector store.

Tests the embedding service implementations and FAISS-based vector store.
"""
import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from backend.logic.embedding_service import (
    MockEmbeddingService,
    create_embedding_service,
)
from backend.logic.vector_store import (
    ThreatMatch,
    ThreatRecord,
    VectorMemory,
)


class TestMockEmbeddingService:
    def test_embed_returns_correct_dimension(self):
        service = MockEmbeddingService(dimension=384)
        embedding = service.embed("example.com")
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32

    def test_embed_returns_normalized_vector(self):
        service = MockEmbeddingService(dimension=128)
        embedding = service.embed("test-domain.com")
        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-6)

    def test_embed_batch_returns_multiple_embeddings(self):
        service = MockEmbeddingService(dimension=256)
        texts = ["domain1.com", "domain2.com", "domain3.com"]
        embeddings = service.embed_batch(texts)
        assert len(embeddings) == 3
        for emb in embeddings:
            assert emb.shape == (256,)

    def test_embed_deterministic(self):
        service = MockEmbeddingService(dimension=128)
        emb1 = service.embed("example.com")
        emb2 = service.embed("example.com")
        np.testing.assert_array_almost_equal(emb1, emb2)

    def test_embed_different_texts_different_vectors(self):
        service = MockEmbeddingService(dimension=128)
        emb1 = service.embed("google.com")
        emb2 = service.embed("malware-site.xyz")
        assert not np.allclose(emb1, emb2)

    def test_get_dimension(self):
        service = MockEmbeddingService(dimension=512)
        assert service.get_dimension() == 512

    def test_is_available(self):
        service = MockEmbeddingService()
        assert service.is_available() is True


class TestCreateEmbeddingService:
    def test_creates_mock_service(self):
        service = create_embedding_service(provider="mock")
        assert isinstance(service, MockEmbeddingService)

    def test_creates_service_with_custom_model(self):
        service = create_embedding_service(provider="mock", model="test-model")
        assert isinstance(service, MockEmbeddingService)

    def test_unknown_provider_falls_back_to_mock(self):
        service = create_embedding_service(provider="unknown-provider")
        assert isinstance(service, MockEmbeddingService)


class TestThreatRecord:
    def test_create_threat_record(self):
        record = ThreatRecord(
            domain="malicious.example.com",
            risk_score="High",
            category="Malware",
            summary="Known malware distribution site",
            timestamp="2024-01-20T12:00:00Z",
            metadata={"source": "test"},
        )
        assert record.domain == "malicious.example.com"
        assert record.risk_score == "High"
        assert record.category == "Malware"

    def test_to_dict(self):
        record = ThreatRecord(
            domain="test.com",
            risk_score="Medium",
            category="Phishing",
            summary="Phishing site",
            timestamp="2024-01-20T12:00:00Z",
            metadata={"confidence": 0.9},
        )
        data = record.to_dict()
        assert data["domain"] == "test.com"
        assert data["risk_score"] == "Medium"
        assert data["metadata"]["confidence"] == 0.9

    def test_from_dict(self):
        data = {
            "domain": "example.com",
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": "Safe domain",
            "timestamp": "2024-01-20T12:00:00Z",
            "metadata": {"verified": True},
        }
        record = ThreatRecord.from_dict(data)
        assert record.domain == "example.com"
        assert record.risk_score == "Low"
        assert record.metadata["verified"] is True


class TestThreatMatch:
    def test_create_threat_match(self):
        record = ThreatRecord(
            domain="test.com",
            risk_score="High",
            category="Malware",
            summary="Test",
            timestamp="2024-01-20T12:00:00Z",
            metadata={},
        )
        match = ThreatMatch(record=record, similarity=0.95)
        assert match.similarity == 0.95
        assert match.record.domain == "test.com"

    def test_to_dict(self):
        record = ThreatRecord(
            domain="malware.com",
            risk_score="Critical",
            category="Malware",
            summary="Malware distribution",
            timestamp="2024-01-20T12:00:00Z",
            metadata={},
        )
        match = ThreatMatch(record=record, similarity=0.8765)
        data = match.to_dict()
        assert data["domain"] == "malware.com"
        assert data["similarity"] == 0.8765


class TestVectorMemory:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_embedding_service(self):
        return MockEmbeddingService(dimension=384)

    def test_initialization(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        assert vm._available is True
        assert vm._dimension == 384
        assert len(vm._metadata) == 0

    def test_add_to_memory(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        result = vm.add_to_memory(
            "malicious.example.com",
            {"risk_score": "High", "category": "Malware"},
            persist=False,
        )
        assert result is True
        assert len(vm._metadata) == 1

    def test_add_multiple_to_memory(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        domains = ["domain1.com", "domain2.com", "domain3.com"]
        for domain in domains:
            vm.add_to_memory(
                domain,
                {"risk_score": "Medium", "category": "Unknown"},
                persist=False,
            )
        assert len(vm._metadata) == 3

    def test_query_empty_memory(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        results = vm.query_memory("test.com")
        assert results == []

    def test_query_returns_similar_threats(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
            similarity_threshold=0.5,
        )
        vm.add_to_memory(
            "malware-site.com",
            {"risk_score": "High", "category": "Malware"},
            persist=False,
        )
        vm.add_to_memory(
            "phishing-site.com",
            {"risk_score": "High", "category": "Phishing"},
            persist=False,
        )
        results = vm.query_memory("malware-site.com", k=5)
        assert len(results) >= 1

    def test_query_respects_threshold(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
            similarity_threshold=0.99,
        )
        vm.add_to_memory(
            "unique-domain-xyz.com",
            {"risk_score": "High", "category": "Malware"},
            persist=False,
        )
        results = vm.query_memory("completely-different-abc.com")
        assert len(results) <= 1

    def test_persist_and_load(self, temp_dir, mock_embedding_service):
        vm1 = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        vm1.add_to_memory(
            "persistent-domain.com",
            {"risk_score": "High", "category": "Malware"},
            persist=True,
        )

        vm2 = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        assert len(vm2._metadata) == 1
        assert vm2._metadata[0].domain == "persistent-domain.com"

    def test_clear_memory(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        vm.add_to_memory("domain1.com", {"risk_score": "High"}, persist=False)
        vm.add_to_memory("domain2.com", {"risk_score": "Medium"}, persist=False)
        assert len(vm._metadata) == 2

        vm.clear_memory()
        assert len(vm._metadata) == 0

    def test_get_stats(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
            similarity_threshold=0.85,
        )
        vm.add_to_memory("test.com", {"risk_score": "High"}, persist=False)
        stats = vm.get_stats()

        assert stats["total_embeddings"] == 1
        assert stats["dimension"] == 384
        assert stats["similarity_threshold"] == 0.85
        assert stats["is_available"] is True

    def test_find_similar_threats(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
            similarity_threshold=0.5,
        )
        vm.add_to_memory(
            "malware-1.com",
            {"risk_score": "High", "category": "Malware", "summary": "Malware C2"},
            persist=False,
        )
        vm.add_to_memory(
            "malware-2.com",
            {"risk_score": "High", "category": "Malware", "summary": "Malware distribution"},
            persist=False,
        )

        matches = vm.find_similar_threats("malware-1.com", k=5)
        assert len(matches) >= 1
        assert all(isinstance(m, ThreatMatch) for m in matches)

    def test_get_threat_cluster(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
            similarity_threshold=0.5,
        )
        vm.add_to_memory("cluster-a.com", {"risk_score": "High"}, persist=False)
        vm.add_to_memory("cluster-b.com", {"risk_score": "High"}, persist=False)

        cluster = vm.get_threat_cluster("cluster-a.com", min_similarity=0.5)
        assert isinstance(cluster, list)

    def test_no_embedding_service(self, temp_dir):
        vm = VectorMemory(
            embedding_service=None,
            index_path=temp_dir,
        )
        assert vm._available is False
        result = vm.add_to_memory("test.com", {"risk_score": "High"})
        assert result is False


class TestVectorMemoryPersistence:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_embedding_service(self):
        return MockEmbeddingService(dimension=128)

    def test_metadata_file_created(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        vm.add_to_memory("test.com", {"risk_score": "High"}, persist=True)

        metadata_path = Path(temp_dir) / "metadata.json"
        assert metadata_path.exists()

        with open(metadata_path) as f:
            data = json.load(f)
        assert len(data["records"]) == 1
        assert data["records"][0]["domain"] == "test.com"

    def test_dimension_persisted(self, temp_dir, mock_embedding_service):
        vm = VectorMemory(
            embedding_service=mock_embedding_service,
            index_path=temp_dir,
        )
        vm.add_to_memory("test.com", {"risk_score": "High"}, persist=True)

        metadata_path = Path(temp_dir) / "metadata.json"
        with open(metadata_path) as f:
            data = json.load(f)
        assert data["dimension"] == 128
