import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from backend.main import app
from backend.core.config import settings
from backend.services.gemini_analyzer import analyze_domain
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
    assert is_valid_domain("example.com") == True
    assert is_valid_domain("sub.example.com") == True
    
    # Invalid domains
    assert is_valid_domain("example com") == False  # Contains space
    assert is_valid_domain("example") == False      # No dot
    assert is_valid_domain("") == False             # Empty
    assert is_valid_domain("http://example.com") == False  # Contains protocol

@patch('backend.services.gemini_analyzer.analyze_domain')
def test_circuit_breaker(mock_analyze):
    # Mock Gemini API failure (429 error)
    mock_analyze.side_effect = Exception("429: Too Many Requests")
    
    # Test that fallback works
    result = analyze_domain("test.com")
    assert result["risk_score"] in ["High", "Low"]
    assert result["category"] in ["Privacy Risk", "Malicious Pattern", "General Traffic"]
    assert "SOC GUARD ACTIVE" in result["summary"]

def test_configuration_validation():
    # Test that missing critical config fails
    with pytest.raises(SystemExit):
        # Mock missing GEMINI_API_KEY
        with patch.dict('os.environ', {'GEMINI_API_KEY': '', 'GOOGLE_SHEETS_CREDENTIALS': 'valid', 'GOOGLE_SHEET_ID': 'valid'}):
            from backend.core.config import settings
            assert not settings.is_valid
    
    # Test valid configuration
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'valid', 'GOOGLE_SHEETS_CREDENTIALS': 'valid', 'GOOGLE_SHEET_ID': 'valid'}):
        from backend.core.config import settings
        assert settings.is_valid

def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "ok"

def test_api_models():
    response = client.get("/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def test_api_analyze():
    # Test with valid domain
    response = client.post("/analyze", json={"domain": "example.com"})
    assert response.status_code == 200
    assert "risk_score" in response.json()
    assert "category" in response.json()
    assert "summary" in response.json()

def test_api_chat():
    # Test chat endpoint
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert "text" in response.json()