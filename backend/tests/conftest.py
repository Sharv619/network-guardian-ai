import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_gemini_response() -> dict[str, Any]:
    """Mock Gemini API response for threat analysis."""
    return {
        "risk_score": "High",
        "category": "Malware",
        "summary": "This domain exhibits suspicious characteristics typical of malware distribution.",
    }


@pytest.fixture
def mock_gemini_low_risk_response() -> dict[str, Any]:
    """Mock Gemini API response for low-risk domain."""
    return {
        "risk_score": "Low",
        "category": "General Traffic",
        "summary": "This domain appears to be legitimate with no suspicious indicators.",
    }


@pytest.fixture
def mock_adguard_log_entry() -> dict[str, Any]:
    """Mock AdGuard query log entry."""
    return {
        "question": {"name": "suspicious-domain.com"},
        "reason": "Blocked",
        "filterId": 2,
        "rule": "||suspicious-domain.com^",
        "client": "192.168.1.100",
        "elapsedMs": 5,
    }


@pytest.fixture
def mock_adguard_allowed_entry() -> dict[str, Any]:
    """Mock AdGuard allowed query log entry."""
    return {
        "question": {"name": "google.com"},
        "reason": "NotFilteredNotFound",
        "filterId": None,
        "rule": "",
        "client": "192.168.1.100",
        "elapsedMs": 3,
    }


@pytest.fixture
def sample_domain_analysis() -> dict[str, Any]:
    """Sample domain analysis result."""
    return {
        "domain": "test-malware-site.com",
        "entropy": 4.2,
        "risk_score": "High",
        "category": "Malware",
        "summary": "High entropy domain with suspicious naming pattern.",
        "is_anomaly": True,
        "anomaly_score": -0.35,
        "analysis_source": "entropy_heuristic",
        "timestamp": "2026-02-20T12:00:00Z",
        "adguard_metadata": {
            "reason": "Blocked",
            "filter_id": 2,
            "rule": "||test-malware-site.com^",
            "client": "192.168.1.100",
        },
        "features": {
            "length": 20,
            "digit_ratio": 0.05,
            "vowel_ratio": 0.3,
            "non_alphanumeric": 1,
        },
    }


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_cache_dir() -> Generator[str, None, None]:
    """Create a temporary directory for cache files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_backup_dir() -> Generator[str, None, None]:
    """Create a temporary directory for backup files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_notion_client():
    """Mock Notion client."""
    client = MagicMock()
    client.pages.create = MagicMock(return_value={"id": "test-page-id"})
    client.databases.query = MagicMock(return_value={"results": []})
    return client


@pytest.fixture
def mock_sheets_client():
    """Mock Google Sheets client."""
    client = MagicMock()
    sheet = MagicMock()
    sheet.append_row = MagicMock()
    sheet.get_all_values = MagicMock(return_value=[])
    client.open_by_key = MagicMock(return_value=MagicMock(sheet1=sheet))
    return client


@pytest.fixture
def mock_alert_webhook():
    """Mock webhook client for alert testing."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        yield mock_post


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("backend.core.config.settings") as mock:
        mock.GEMINI_API_KEY = "test-api-key"
        mock.GEMINI_MODE = "fallback"
        mock.USE_NOTION = False
        mock.USE_SHEETS = False
        mock.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
        mock.BACKUP_ENABLED = False
        mock.RATE_LIMIT_ENABLED = False
        mock.IP_REPUTATION_ENABLED = False
        yield mock


@pytest.fixture
async def async_test_client():
    """Async test client for FastAPI app."""
    from backend.main import app

    async with AsyncClient(
        app=app,
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sync_test_client():
    """Synchronous test client for FastAPI app."""
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def rate_limit_test_ips() -> list[str]:
    """Test IP addresses for rate limiting tests."""
    return [
        "192.168.1.1",
        "192.168.1.2",
        "10.0.0.1",
        "172.16.0.1",
        "8.8.8.8",
    ]


@pytest.fixture
def test_domains() -> list[str]:
    """Test domains for validation tests."""
    return [
        "google.com",
        "example.org",
        "sub.domain.co.uk",
        "test-site123.net",
        "xn--n3h.com",
        "very-long-subdomain.example.com",
    ]


@pytest.fixture
def invalid_domains() -> list[str]:
    """Invalid domains for validation tests."""
    return [
        "",
        ".",
        "..",
        "-invalid.com",
        "invalid-.com",
        "invalid..domain.com",
        "a" * 300 + ".com",
        "localhost",
        ".example.com",
    ]


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    from backend.logic.anomaly_engine import engine as anomaly_engine
    from backend.logic.metadata_classifier import classifier
    from backend.logic.vector_store import vector_memory
    from backend.core.rate_limiter import multi_rate_limiter

    anomaly_engine.history = []
    anomaly_engine.is_trained = False
    classifier.local_decisions_count = 0
    classifier.cloud_decisions_count = 0
    classifier.patterns.clear()
    vector_memory.clear_memory()

    for limiter in multi_rate_limiter.limiters.values():
        limiter.requests.clear()

    yield


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = {
        "risk_score": "Low",
        "category": "General Traffic",
        "summary": "Safe domain with no suspicious indicators."
    }
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_gemini_malicious_client():
    """Create a mock Gemini client that returns malicious response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = {
        "risk_score": "High",
        "category": "Malware",
        "summary": "Domain exhibits DGA patterns and suspicious characteristics."
    }
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_gemini_chat_client():
    """Create a mock Gemini client for chat."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "I can help you analyze network threats."
    mock_client.models.generate_content.return_value = mock_response
    return mock_client
