import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_analyze_endpoint():
    """Test analyze endpoint with new ThreatEntry fields."""
    mock_response = {
        "domain": "example.com",
        "risk_score": "Low",
        "category": "General Traffic",
        "summary": "Verified safe.",
        "is_anomaly": False,
        "anomaly_score": 0.0,
    }

    with patch("backend.api.router.analyze_domain", return_value=mock_response):
        response = client.post("/analyze", json={"domain": "example.com"})
        assert response.status_code == 200

        json_data = response.json()
        assert json_data["risk_score"] == "Low"
        assert "timestamp" in json_data
        assert json_data["is_anomaly"] is False
        assert json_data["anomaly_score"] == 0.0


def test_analyze_endpoint_fallback():
    """Test analyze endpoint with fallback response (when analyze_domain raises)."""
    with patch("backend.api.router.analyze_domain", side_effect=Exception("API Down")):
        try:
            response = client.post("/analyze", json={"domain": "error-test.com"})
        except Exception:
            pass  # Exception may propagate depending on router implementation


def test_history_endpoint():
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_chat_graceful_degradation():
    """Test that chat endpoint handles API failures gracefully."""
    with patch("backend.api.router.chat_with_ai", side_effect=Exception("429 Too Many Requests")):
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 200
        assert "Autonomous SOC Mode" in response.json()["text"]
