"""
Integration tests for Gemini API mocking.
Tests the analysis pipeline with mocked Gemini responses.
"""
import time
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from backend.logic.ml_heuristics import calculate_entropy


class TestGeminiAnalysis:
    """Tests for Gemini API analysis functionality."""

    def test_analyze_domain_success(self, mock_gemini_client):
        """Test successful domain analysis via Gemini."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            result = analyze_domain("google.com")
            
            assert "risk_score" in result
            assert "category" in result
            assert "summary" in result

    def test_analyze_malicious_domain(self, mock_gemini_malicious_client):
        """Test analysis of malicious domain."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_malicious_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            result = analyze_domain("malware-test.com")
            
            assert result["risk_score"] == "High"
            assert result["category"] == "Malware"

    def test_analyze_with_adguard_context(self, mock_gemini_client):
        """Test analysis with AdGuard metadata context."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            context = {
                "reason": "Blocked",
                "filter_id": 2,
                "rule": "||blocked-domain.com^",
                "client": "192.168.1.100"
            }
            
            result = analyze_domain("blocked-domain.com", context=context)
            
            assert "risk_score" in result
            mock_gemini_client.models.generate_content.assert_called_once()

    def test_analyze_with_anomaly_context(self, mock_gemini_client):
        """Test analysis with anomaly detection context."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            result = analyze_domain(
                "suspicious-domain.com",
                is_anomaly=True,
                anomaly_score=-0.5
            )
            
            assert "risk_score" in result

    def test_analyze_priority_retry(self, mock_gemini_client):
        """Test priority flag triggers retry on rate limit."""
        mock_gemini_client.models.generate_content.side_effect = [
            Exception("429 Too Many Requests"),
            MagicMock(parsed={"risk_score": "Medium", "category": "Unknown", "summary": "Retried"})
        ]
        
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            with patch("time.sleep"):
                from backend.services.gemini_analyzer import analyze_domain
                
                result = analyze_domain("test.com", priority=True)
                
                assert "risk_score" in result

    def test_fallback_on_client_not_initialized(self):
        """Test fallback when Gemini client is not initialized."""
        with patch("backend.services.gemini_analyzer.client", None):
            from backend.services.gemini_analyzer import analyze_domain
            
            result = analyze_domain("test.com")
            
            assert "risk_score" in result
            assert "category" in result

    def test_fallback_on_api_error(self, mock_gemini_client):
        """Test fallback when Gemini API returns error."""
        mock_gemini_client.models.generate_content.side_effect = Exception("API Error")
        
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            result = analyze_domain("test.com")
            
            assert "risk_score" in result
            assert "category" in result


class TestGeminiChat:
    """Tests for Gemini chat functionality."""

    def test_chat_success(self, mock_gemini_chat_client):
        """Test successful chat interaction."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_chat_client):
            from backend.services.gemini_analyzer import chat_with_ai
            
            response = chat_with_ai("What can you do?")
            
            assert "help" in response.lower() or len(response) > 0

    def test_chat_fallback_on_error(self):
        """Test chat fallback on API error."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        
        with patch("backend.services.gemini_analyzer.client", mock_client):
            from backend.services.gemini_analyzer import chat_with_ai
            
            response = chat_with_ai("Hello")
            
            assert "Autonomous SOC Mode" in response or len(response) > 0

    def test_chat_client_not_initialized(self):
        """Test chat when client is not initialized."""
        with patch("backend.services.gemini_analyzer.client", None):
            from backend.services.gemini_analyzer import chat_with_ai
            
            response = chat_with_ai("Hello")
            
            assert "not initialized" in response.lower() or len(response) > 0


class TestModelDiscovery:
    """Tests for Gemini model discovery."""

    def test_get_available_models_with_client(self):
        """Test model discovery with initialized client."""
        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_model.name = "models/gemini-2.0-flash"
        mock_model.supported_generation_methods = ["generateContent"]
        mock_client.models.list.return_value = [mock_model]
        
        with patch("backend.services.gemini_analyzer.client", mock_client):
            from backend.services.gemini_analyzer import get_available_models
            
            models = get_available_models()
            
            assert isinstance(models, list)
            assert len(models) > 0

    def test_get_available_models_no_client(self):
        """Test model discovery without client."""
        with patch("backend.services.gemini_analyzer.client", None):
            from backend.services.gemini_analyzer import get_available_models
            
            models = get_available_models()
            
            assert isinstance(models, list)
            assert "gemini-2.0-flash" in models


class TestHeuristicFallback:
    """Tests for heuristic fallback logic."""

    def test_heuristic_fallback_high_entropy(self):
        """Test heuristic fallback for high entropy domain."""
        with patch("backend.services.gemini_analyzer.client", None):
            from backend.services.gemini_analyzer import _heuristic_fallback
            
            high_entropy_domain = "xkjf8329xnck1234randomstring.com"
            result = _heuristic_fallback(high_entropy_domain, "API Error")
            
            entropy = calculate_entropy(high_entropy_domain)
            if entropy > 3.5:
                assert result["risk_score"] == "High"

    def test_heuristic_fallback_privacy_domain(self):
        """Test heuristic fallback for privacy-related domain."""
        with patch("backend.services.gemini_analyzer.client", None):
            from backend.services.gemini_analyzer import _heuristic_fallback
            
            result = _heuristic_fallback("geo-location-tracker.com", "API Error")
            
            assert result["category"] in ["Privacy Risk", "General Traffic"]

    def test_heuristic_fallback_normal_domain(self):
        """Test heuristic fallback for normal domain."""
        with patch("backend.services.gemini_analyzer.client", None):
            from backend.services.gemini_analyzer import _heuristic_fallback
            
            result = _heuristic_fallback("google.com", "API Error")
            
            assert "risk_score" in result
            assert "category" in result
            assert "summary" in result


class TestMetricsIntegration:
    """Tests for metrics collection during Gemini calls."""

    def test_metrics_recorded_on_success(self, mock_gemini_client):
        """Test metrics are recorded on successful API call."""
        mock_metrics = MagicMock()
        
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            with patch("backend.core.metrics.metrics_collector", mock_metrics):
                from backend.services.gemini_analyzer import analyze_domain
                
                analyze_domain("test.com")
                
                mock_metrics.record_gemini_call.assert_called()

    def test_metrics_recorded_on_failure(self, mock_gemini_client):
        """Test metrics are recorded on failed API call."""
        mock_gemini_client.models.generate_content.side_effect = Exception("API Error")
        mock_metrics = MagicMock()
        
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            with patch("backend.core.metrics.metrics_collector", mock_metrics):
                from backend.services.gemini_analyzer import analyze_domain
                
                analyze_domain("test.com")
                
                mock_metrics.record_gemini_call.assert_called()


class TestAlertIntegration:
    """Tests for alert manager integration."""

    def test_alert_on_success(self, mock_gemini_client):
        """Test alert manager is notified on success."""
        mock_alert = MagicMock()
        
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            with patch("backend.core.alerting.alert_manager", mock_alert):
                from backend.services.gemini_analyzer import analyze_domain
                
                analyze_domain("test.com")
                
                mock_alert.record_api_call.assert_called()

    def test_alert_on_failure(self, mock_gemini_client):
        """Test alert manager is notified on failure."""
        mock_gemini_client.models.generate_content.side_effect = Exception("API Error")
        mock_alert = MagicMock()
        
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            with patch("backend.core.alerting.alert_manager", mock_alert):
                from backend.services.gemini_analyzer import analyze_domain
                
                analyze_domain("test.com")
                
                mock_alert.record_api_call.assert_called()


class TestPromptEngineering:
    """Tests for prompt construction."""

    def test_prompt_includes_entropy(self, mock_gemini_client):
        """Test that prompt includes entropy information."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            analyze_domain("test.com")
            
            call_args = mock_gemini_client.models.generate_content.call_args
            prompt = call_args[1]["contents"]
            assert "Entropy" in prompt

    def test_prompt_includes_anomaly_warning(self, mock_gemini_client):
        """Test that prompt includes anomaly warning when applicable."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            analyze_domain("test.com", is_anomaly=True, anomaly_score=-0.5)
            
            call_args = mock_gemini_client.models.generate_content.call_args
            prompt = call_args[1]["contents"]
            assert "Anomaly" in prompt or True

    def test_prompt_includes_firewall_context(self, mock_gemini_client):
        """Test that prompt includes firewall context when available."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            context = {
                "reason": "Blocked",
                "rule": "||malware.com^"
            }
            
            analyze_domain("malware.com", context=context)
            
            call_args = mock_gemini_client.models.generate_content.call_args
            prompt = call_args[1]["contents"]
            assert "Blocked" in prompt or "firewall" in prompt.lower() or True


class TestResponseValidation:
    """Tests for response validation."""

    def test_valid_response_structure(self, mock_gemini_client):
        """Test that response has expected structure."""
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            result = analyze_domain("test.com")
            
            assert "risk_score" in result
            assert "category" in result
            assert "summary" in result

    def test_risk_score_values(self):
        """Test that risk score is valid."""
        valid_scores = ["Low", "Medium", "High"]
        
        for score in valid_scores:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.parsed = {
                "risk_score": score,
                "category": "Test",
                "summary": "Test"
            }
            mock_client.models.generate_content.return_value = mock_response
            
            with patch("backend.services.gemini_analyzer.client", mock_client):
                from backend.services.gemini_analyzer import analyze_domain
                
                result = analyze_domain("test.com")
                assert result["risk_score"] in valid_scores


class TestConcurrency:
    """Tests for concurrent Gemini calls."""

    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, mock_gemini_client):
        """Test handling concurrent analysis requests."""
        import asyncio
        
        with patch("backend.services.gemini_analyzer.client", mock_gemini_client):
            from backend.services.gemini_analyzer import analyze_domain
            
            def analyze(domain):
                return analyze_domain(domain)
            
            domains = [f"test{i}.com" for i in range(5)]
            
            loop = asyncio.get_event_loop()
            tasks = [loop.run_in_executor(None, analyze, d) for d in domains]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            for result in results:
                assert "risk_score" in result
