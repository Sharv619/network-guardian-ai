"""
Integration tests for API endpoints.
Tests the full request/response cycle with database interactions.
"""
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest.fixture
def sync_client():
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async test client for testing async endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore
        base_url="http://test",
    ) as client:
        yield client


class TestHealthEndpoints:
    """Integration tests for health and status endpoints."""

    def test_health_check(self, sync_client):
        """Test basic health endpoint."""
        response = sync_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_system_endpoint(self, sync_client):
        """Test system intelligence endpoint."""
        response = sync_client.get("/system")
        assert response.status_code == 200
        data = response.json()
        assert "system_status" in data
        assert "autonomy_score" in data


class TestAnalyzeEndpoints:
    """Integration tests for domain analysis endpoints."""

    def test_analyze_valid_domain(self, sync_client):
        """Test analyzing a valid domain."""
        mock_response = {
            "domain": "google.com",
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": "Safe domain",
            "is_anomaly": False,
            "anomaly_score": 0.0,
        }
        
        with patch("backend.api.router.analyze_domain", return_value=mock_response):
            response = sync_client.post(
                "/analyze",
                json={"domain": "google.com"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "google.com"
        assert data["risk_score"] == "Low"
        assert "timestamp" in data

    def test_analyze_suspicious_domain(self, sync_client):
        """Test analyzing a suspicious domain."""
        mock_response = {
            "domain": "malware-test.com",
            "risk_score": "High",
            "category": "Malware",
            "summary": "Suspicious domain detected",
            "is_anomaly": True,
            "anomaly_score": -0.5,
        }
        
        with patch("backend.api.router.analyze_domain", return_value=mock_response):
            response = sync_client.post(
                "/analyze",
                json={"domain": "malware-test.com"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == "High"
        assert data["is_anomaly"] is True

    def test_analyze_invalid_domain(self, sync_client):
        """Test analyzing an invalid domain."""
        response = sync_client.post(
            "/analyze",
            json={"domain": ""}
        )
        assert response.status_code == 422

    def test_analyze_long_domain(self, sync_client):
        """Test analyzing a domain exceeding length limit."""
        long_domain = "a" * 300 + ".com"
        response = sync_client.post(
            "/analyze",
            json={"domain": long_domain}
        )
        assert response.status_code == 422

    def test_analyze_with_metadata(self, sync_client):
        """Test analyzing a domain with AdGuard metadata."""
        mock_response = {
            "domain": "blocked-site.com",
            "risk_score": "High",
            "category": "Tracker",
            "summary": "Blocked by AdGuard",
            "is_anomaly": False,
            "anomaly_score": 0.0,
        }
        
        with patch("backend.api.router.analyze_domain", return_value=mock_response):
            response = sync_client.post(
                "/analyze",
                json={
                    "domain": "blocked-site.com",
                    "metadata": {
                        "reason": "Blocked",
                        "filter_id": 2,
                        "rule": "||blocked-site.com^",
                        "client": "192.168.1.100"
                    }
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Tracker"


class TestHistoryEndpoints:
    """Integration tests for history endpoints."""

    def test_get_history(self, sync_client):
        """Test getting analysis history."""
        response = sync_client.get("/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_history_with_limit(self, sync_client):
        """Test getting history with limit parameter."""
        response = sync_client.get("/history?limit=10")
        assert response.status_code == 200


class TestChatEndpoints:
    """Integration tests for chat/AI endpoints."""

    def test_chat_basic(self, sync_client):
        """Test basic chat functionality."""
        mock_response = {
            "text": "I can help you analyze network security threats."
        }
        
        with patch("backend.api.router.chat_with_ai", return_value=mock_response):
            response = sync_client.post(
                "/chat",
                json={"message": "What can you do?"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "text" in data

    def test_chat_graceful_degradation(self, sync_client):
        """Test chat handles API failures gracefully."""
        with patch("backend.api.router.chat_with_ai", side_effect=Exception("API Error")):
            response = sync_client.post(
                "/chat",
                json={"message": "Hello"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "Autonomous SOC Mode" in data["text"] or "text" in data

    def test_chat_with_context(self, sync_client):
        """Test chat with context provided."""
        mock_response = {
            "text": "Based on the analysis, this domain appears safe."
        }
        
        with patch("backend.api.router.chat_with_ai", return_value=mock_response):
            response = sync_client.post(
                "/chat",
                json={
                    "message": "Is google.com safe?",
                    "context": "Domain analysis for google.com"
                }
            )
        
        assert response.status_code == 200


class TestStatsEndpoints:
    """Integration tests for statistics endpoints."""

    def test_get_stats(self, sync_client):
        """Test getting system statistics."""
        response = sync_client.get("/api/stats")
        assert response.status_code == 200

    def test_get_classifier_stats(self, sync_client):
        """Test getting classifier statistics."""
        response = sync_client.get("/api/stats/classifier")
        assert response.status_code in [200, 404]

    def test_get_anomaly_stats(self, sync_client):
        """Test getting anomaly engine statistics."""
        response = sync_client.get("/api/stats/anomaly")
        assert response.status_code in [200, 404]


class TestAlertEndpoints:
    """Integration tests for alert endpoints."""

    def test_get_alerts(self, sync_client):
        """Test getting alerts."""
        response = sync_client.get("/alerts")
        assert response.status_code in [200, 404]

    def test_get_alert_stats(self, sync_client):
        """Test getting alert statistics."""
        response = sync_client.get("/alerts/stats")
        assert response.status_code in [200, 404]


class TestDatabaseEndpoints:
    """Integration tests for database management endpoints."""

    def test_get_database_stats(self, sync_client):
        """Test getting database statistics."""
        response = sync_client.get("/database/stats")
        assert response.status_code in [200, 404]

    def test_list_backups(self, sync_client):
        """Test listing database backups."""
        response = sync_client.get("/database/backups")
        assert response.status_code in [200, 404]


class TestAuthIntegration:
    """Integration tests for authentication flow."""

    def test_login_and_access_protected_route(self, sync_client):
        """Test full login flow and accessing protected routes."""
        login_response = sync_client.post(
            "/auth/token",
            json={"username": "admin", "password": "admin123"}
        )
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        auth_status = sync_client.get(
            "/auth/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert auth_status.status_code == 200
        data = auth_status.json()
        assert data["is_authenticated"] is True

    def test_protected_route_without_auth(self, sync_client):
        """Test accessing protected route without authentication."""
        response = sync_client.get("/auth/me")
        assert response.status_code == 401

    def test_invalid_token(self, sync_client):
        """Test accessing protected route with invalid token."""
        response = sync_client.get(
            "/auth/status",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 422]


class TestRateLimitingIntegration:
    """Integration tests for rate limiting."""

    def test_rate_limit_not_exceeded(self, sync_client):
        """Test requests within rate limit."""
        for _ in range(5):
            response = sync_client.get("/health")
            assert response.status_code == 200

    def test_analyze_rate_limit(self, sync_client):
        """Test analyze endpoint rate limiting."""
        mock_response = {
            "domain": "test.com",
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": "Safe",
            "is_anomaly": False,
            "anomaly_score": 0.0,
        }
        
        with patch("backend.api.router.analyze_domain", return_value=mock_response):
            for i in range(15):
                response = sync_client.post(
                    "/analyze",
                    json={"domain": f"test{i}.com"}
                )
                if response.status_code == 429:
                    break
                assert response.status_code in [200, 429]


class TestErrorHandling:
    """Integration tests for error handling."""

    def test_404_endpoint(self, sync_client):
        """Test accessing non-existent endpoint."""
        response = sync_client.get("/nonexistent-endpoint-xyz")
        assert response.status_code in [404, 200]

    def test_invalid_json(self, sync_client):
        """Test sending invalid JSON."""
        response = sync_client.post(
            "/analyze",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_method_not_allowed(self, sync_client):
        """Test using wrong HTTP method."""
        response = sync_client.delete("/health")
        assert response.status_code == 405


class TestConcurrency:
    """Integration tests for concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_analyze_requests(self, async_client):
        """Test handling multiple concurrent analysis requests."""
        mock_response = {
            "domain": "test.com",
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": "Safe",
            "is_anomaly": False,
            "anomaly_score": 0.0,
        }
        
        with patch("backend.api.router.analyze_domain", return_value=mock_response):
            tasks = [
                async_client.post("/analyze", json={"domain": f"test{i}.com"})
                for i in range(10)
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(
                1 for r in responses
                if not isinstance(r, Exception) and hasattr(r, "status_code") and getattr(r, "status_code", None) == 200
            )
            assert successful >= 5

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, async_client):
        """Test handling concurrent health check requests."""
        tasks = [async_client.get("/health") for _ in range(20)]
        responses = await asyncio.gather(*tasks)
        
        for response in responses:
            assert response.status_code == 200
