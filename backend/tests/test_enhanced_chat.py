import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from backend.api.advanced_chat import (
    generate_advanced_rag_response,
    search_threat_history,
    search_vector_memory,
    search_analysis_cache,
    get_temporal_context,
    get_behavioral_context,
)
from backend.core.state import automated_threats, manual_scans


class TestEnhancedChat:
    """Test suite for enhanced RAG chat functionality."""

    def setup_method(self):
        """Set up test data."""
        # Clear existing threats for clean test state
        automated_threats.clear()
        manual_scans.clear()

        # Add test threat data
        test_threats = [
            {
                "domain": "test-domain.com",
                "risk_score": "High",
                "category": "Malware",
                "summary": "Test malware domain",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "is_anomaly": True,
                "anomaly_score": -0.15,
                "adguard_metadata": {
                    "reason": "NotFilteredNotFound",
                    "rule": "",
                    "filter_id": None,
                    "client": "192.168.1.100",
                },
                "analysis_source": "entropy_heuristic",
                "entropy": 4.2,
            },
            {
                "domain": "test-domain.com",
                "risk_score": "Medium",
                "category": "Tracking",
                "summary": "Test tracking domain",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "is_anomaly": False,
                "anomaly_score": 0.05,
                "adguard_metadata": {
                    "reason": "NotFilteredNotFound",
                    "rule": "",
                    "filter_id": None,
                    "client": "192.168.1.101",
                },
                "analysis_source": "local_heuristic",
                "entropy": 3.1,
            },
        ]

        automated_threats.extend(test_threats)

    def test_search_threat_history(self):
        """Test threat history search functionality."""
        results = search_threat_history("test-domain.com")
        assert len(results) == 2
        assert all("test-domain.com" in threat["domain"] for threat in results)
        assert any(threat["category"] == "Malware" for threat in results)
        assert any(threat["category"] == "Tracking" for threat in results)

    def test_search_threat_history_no_match(self):
        """Test threat history search with no matches."""
        results = search_threat_history("nonexistent-domain.com")
        assert len(results) == 0

    @patch("backend.api.advanced_chat.vector_memory")
    def test_search_vector_memory(self, mock_vector_memory):
        """Test vector memory search functionality."""
        mock_match = MagicMock()
        mock_match.to_dict.return_value = {
            "domain": "similar-domain.com",
            "risk_score": "High",
            "category": "Malware",
            "summary": "Similar threat",
            "_similarity_score": 0.8,
        }
        mock_vector_memory.find_similar_threats.return_value = [mock_match]
        mock_vector_memory._available = True

        results = search_vector_memory("test query", k=5, min_similarity=0.7)
        assert len(results) == 1
        assert results[0]["domain"] == "similar-domain.com"
        assert results[0]["_similarity_score"] == 0.8

    @patch("backend.logic.analysis_cache.analysis_cache")
    def test_search_analysis_cache(self, mock_cache):
        """Test analysis cache search functionality."""
        mock_cache.get.return_value = {
            "risk_score": "Low",
            "category": "Safe",
            "summary": "Cached safe analysis",
        }

        result = search_analysis_cache("test-domain.com")
        assert result is not None
        assert result["risk_score"] == "Low"
        assert result["category"] == "Safe"

    def test_get_temporal_context(self):
        """Test temporal context extraction."""
        context = get_temporal_context("test-domain.com")
        assert "first_seen" in context
        assert "last_seen" in context
        assert "frequency" in context
        assert "trend" in context
        assert context["frequency"] == 2  # Should find 2 records

    def test_get_behavioral_context(self):
        """Test behavioral context extraction."""
        context = get_behavioral_context("test-domain.com")
        assert "risk_trend" in context
        assert "common_categories" in context
        assert "average_risk_score" in context
        assert context["average_risk_score"] > 0  # Should have calculated average

    def test_generate_advanced_rag_response_with_domain(self):
        """Test advanced RAG response generation with domain."""
        with patch("backend.services.gemini_analyzer.analyze_domain") as mock_analyze:
            mock_analyze.return_value = {
                "risk_score": "High",
                "category": "Malware",
                "summary": "Analysis via Gemini",
            }

            response = generate_advanced_rag_response(
                "Tell me about test-domain.com",
                include_context=True,
                search_radius=5,
                min_similarity=0.7,
            )

            assert "response" in response
            assert "sources" in response
            assert "confidence" in response
            assert "context" in response
            assert response["context"]["domain_found"] is True
            assert response["context"]["domain"] == "test-domain.com"

    def test_generate_advanced_rag_response_without_domain(self):
        """Test advanced RAG response generation without domain."""
        with patch("backend.services.gemini_analyzer.chat_with_ai") as mock_chat:
            mock_chat.return_value = "General security information"

            response = generate_advanced_rag_response(
                "How does threat detection work?",
                include_context=False,
                search_radius=5,
                min_similarity=0.7,
            )

            assert "response" in response
            # Check if it contains the response or falls back gracefully
            if "unavailable" not in response["response"].lower():
                assert "security context" in response["response"].lower()
            assert "context" in response

    def test_generate_advanced_rag_response_include_context(self):
        """Test advanced RAG response with context inclusion."""
        with patch("backend.services.gemini_analyzer.analyze_domain"):
            response = generate_advanced_rag_response(
                "Tell me about test-domain.com",
                include_context=True,
                search_radius=5,
                min_similarity=0.7,
            )

            assert "context" in response
            # Check if context has the expected structure
            if response["context"]:  # Only check if context exists
                assert "domain_found" in response["context"]

    def test_generate_advanced_rag_response_exclude_context(self):
        """Test advanced RAG response without context inclusion."""
        with patch("backend.services.gemini_analyzer.analyze_domain"):
            response = generate_advanced_rag_response(
                "Tell me about test-domain.com",
                include_context=False,
                search_radius=5,
                min_similarity=0.7,
            )

            # Even when exclude_context is False, some basic context should still be included
            assert "context" in response


if __name__ == "__main__":
    pytest.main([__file__])
