import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from backend.main import app
from backend.core.config import settings
from backend.services.gemini_analyzer import analyze_domain, _heuristic_fallback
from backend.logic.ml_heuristics import calculate_entropy, is_valid_domain

client = TestClient(app)


def test_entropy_accuracy():
    # Test DGA-like domain (high entropy)
    high_entropy_domain = "xhk92-z1.ru"
    assert calculate_entropy(high_entropy_domain) > 3.5

    # Test normal domain (low entropy)
    normal_domain = "google.com"
    assert calculate_entropy(normal_domain) < 3.5

    # Test edge cases
    assert calculate_entropy("") == 0.0
    assert calculate_entropy("a") == 0.0


def test_domain_validation():
    # Valid domains
    assert is_valid_domain("example.com") is True
    assert is_valid_domain("sub.example.com") is True

    # Invalid domains
    assert is_valid_domain("example com") is False  # Contains space
    assert is_valid_domain("example") is False      # No dot
    assert is_valid_domain("") is False             # Empty
    # Note: http:// URLs are accepted (function is permissive for URL handling)


def test_circuit_breaker():
    # Test the fallback function directly (not the API-wrapped version)
    result = _heuristic_fallback("test.com", "429: Too Many Requests")
    assert result["risk_score"] in ["High", "Low"]
    assert result["category"] in ["Privacy Risk", "Malicious Pattern", "General Traffic"]
    assert "SOC GUARD ACTIVE" in result["summary"]


def test_configuration_validation():
    # Test the is_valid property with current settings
    assert settings.is_valid is True  # Config is loaded from environment
    assert settings.GEMINI_API_KEY is not None
    assert settings.GOOGLE_SHEETS_CREDENTIALS is not None
    assert settings.GOOGLE_SHEET_ID is not None

    # Test allowed origins parsing
    origins = settings.allowed_origins_list
    assert "http://localhost:3000" in origins
    assert "http://localhost:8000" in origins


def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"


def test_api_models():
    response = client.get("/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Models may be empty if API key has no quota, but endpoint should work


def test_api_analyze():
    # Test with valid domain - mock the analyzer to avoid real API calls
    with patch('backend.api.router.analyze_domain') as mock_analyze:
        mock_analyze.return_value = {
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": "Test analysis"
        }
        response = client.post("/analyze", json={"domain": "example.com"})
        assert response.status_code == 200
        assert "risk_score" in response.json()
        assert "category" in response.json()
        assert "summary" in response.json()


def test_api_chat():
    # Test chat endpoint - mock to avoid real API calls
    with patch('backend.api.router.chat_with_ai') as mock_chat:
        mock_chat.return_value = "Test response"
        response = client.post("/chat", json={"message": "Hello"})
        assert response.status_code == 200
        assert "text" in response.json()