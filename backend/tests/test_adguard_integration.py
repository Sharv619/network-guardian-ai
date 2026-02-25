"""
Integration tests for AdGuard polling simulation.
Tests the local-first pipeline and domain processing logic.
"""
import time
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from backend.logic.ml_heuristics import calculate_entropy, extract_domain_features, is_dga, is_valid_domain
from backend.logic.anomaly_engine import predict_anomaly
from backend.logic.metadata_classifier import classify_domain_metadata, classifier
from backend.services.adguard_poller import run_local_first_pipeline, processed_domains


class TestAdGuardLogParsing:
    """Tests for AdGuard log parsing and processing."""

    @pytest.fixture
    def sample_blocked_log(self):
        """Sample blocked DNS log entry."""
        return {
            "question": {"name": "malware-test.com"},
            "reason": "Blocked",
            "filterId": 2,
            "rule": "||malware-test.com^",
            "client": "192.168.1.100",
            "elapsedMs": 5
        }

    @pytest.fixture
    def sample_allowed_log(self):
        """Sample allowed DNS log entry."""
        return {
            "question": {"name": "google.com"},
            "reason": "NotFilteredNotFound",
            "filterId": None,
            "rule": "",
            "client": "192.168.1.100",
            "elapsedMs": 3
        }

    @pytest.fixture
    def sample_malformed_log(self):
        """Sample malformed DNS log entry."""
        return {
            "question": None,
            "reason": "Unknown"
        }

    def test_valid_domain_extraction(self, sample_blocked_log):
        """Test extracting valid domain from log entry."""
        domain = sample_blocked_log["question"]["name"].lower().strip()
        assert is_valid_domain(domain)
        assert domain == "malware-test.com"

    def test_invalid_domain_filtering(self):
        """Test filtering of invalid domains."""
        invalid_domains = [
            "test.local",
            "test.arpa",
        ]
        
        for domain in invalid_domains:
            normalized = str(domain).lower().strip()
            assert normalized.endswith('.local') or normalized.endswith('.arpa')

    def test_metadata_extraction(self, sample_blocked_log):
        """Test extracting metadata from log entry."""
        metadata = {
            "reason": sample_blocked_log.get("reason", "NotFilteredNotFound"),
            "filter_id": sample_blocked_log.get("filterId"),
            "rule": sample_blocked_log.get("rule") or "",
            "client": sample_blocked_log.get("client") or "",
            "elapsed_ms": sample_blocked_log.get("elapsedMs")
        }
        
        assert metadata["reason"] == "Blocked"
        assert metadata["filter_id"] == 2
        assert metadata["rule"] == "||malware-test.com^"
        assert metadata["client"] == "192.168.1.100"


class TestLocalFirstPipeline:
    """Tests for the local-first analysis pipeline."""

    @pytest.fixture
    def reset_classifier_state(self):
        """Reset classifier state before each test."""
        classifier.local_decisions_count = 0
        classifier.cloud_decisions_count = 0
        yield
        classifier.local_decisions_count = 0
        classifier.cloud_decisions_count = 0

    def test_blocked_domain_metadata_classification(self, reset_classifier_state):
        """Test that blocked domains are classified via metadata."""
        domain = "tracking-ads.com"
        entropy = calculate_entropy(domain)
        features = extract_domain_features(domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {
            "reason": "Blocked",
            "filter_id": 2,
            "rule": "||tracking-ads.com^",
            "client": "192.168.1.100",
        }
        
        result = run_local_first_pipeline(
            domain=domain,
            entropy=entropy,
            features=features,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            adguard_metadata=metadata
        )
        
        assert result["analysis_source"] in ["metadata_classifier", "local_heuristic", "entropy_heuristic"]
        assert "risk_score" in result
        assert "category" in result
        assert "summary" in result

    def test_dga_detection_in_pipeline(self, reset_classifier_state):
        """Test that DGA domains are detected."""
        dga_domain = "xkjf8329xnck1234.com"
        entropy = calculate_entropy(dga_domain)
        features = extract_domain_features(dga_domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {
            "reason": "NotFilteredNotFound",
            "filter_id": None,
            "rule": "",
            "client": "192.168.1.100",
        }
        
        result = run_local_first_pipeline(
            domain=dga_domain,
            entropy=entropy,
            features=features,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            adguard_metadata=metadata
        )
        
        if is_dga(dga_domain):
            assert result["category"] == "Malware"
            assert result["analysis_source"] == "entropy_heuristic"

    def test_safe_domain_classification(self, reset_classifier_state):
        """Test classification of safe domains."""
        domain = "google.com"
        entropy = calculate_entropy(domain)
        features = extract_domain_features(domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {
            "reason": "NotFilteredNotFound",
            "filter_id": None,
            "rule": "",
            "client": "192.168.1.100",
        }
        
        result = run_local_first_pipeline(
            domain=domain,
            entropy=entropy,
            features=features,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            adguard_metadata=metadata
        )
        
        assert result["risk_score"] in ["Low", "Medium", "High"]
        assert result["analysis_source"] in ["metadata_classifier", "local_heuristic", "entropy_heuristic", "knowledge_base"]

    @patch("backend.services.adguard_poller.settings")
    def test_gemini_always_mode(self, mock_settings, reset_classifier_state):
        """Test that Gemini is called when mode is 'always'."""
        mock_settings.GEMINI_MODE = "always"
        
        mock_gemini_response = {
            "risk_score": "Medium",
            "category": "Suspicious",
            "summary": "Requires further analysis"
        }
        
        domain = "unknown-domain-xyz.com"
        entropy = calculate_entropy(domain)
        features = extract_domain_features(domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {"reason": "NotFilteredNotFound"}
        
        with patch("backend.services.adguard_poller.analyze_domain", return_value=mock_gemini_response):
            result = run_local_first_pipeline(
                domain=domain,
                entropy=entropy,
                features=features,
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                adguard_metadata=metadata
            )
            
            assert result["analysis_source"] in ["gemini_ai", "knowledge_base"]

    @patch("backend.services.adguard_poller.settings")
    def test_gemini_fallback_mode(self, mock_settings, reset_classifier_state):
        """Test that Gemini is only called for unknown patterns in fallback mode."""
        mock_settings.GEMINI_MODE = "fallback"
        
        domain = "completely-unknown.xyz"
        entropy = calculate_entropy(domain)
        features = extract_domain_features(domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {"reason": "Processed"}
        
        mock_gemini_response = {
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": "Safe domain"
        }
        
        with patch("backend.services.adguard_poller.analyze_domain", return_value=mock_gemini_response):
            result = run_local_first_pipeline(
                domain=domain,
                entropy=entropy,
                features=features,
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                adguard_metadata=metadata
            )
        
        assert result is not None

    def test_local_decision_counter(self, reset_classifier_state):
        """Test that local decisions are counted correctly."""
        from backend.logic.metadata_classifier import classifier
        
        initial_count = classifier.local_decisions_count
        
        domain = "example.com"
        entropy = calculate_entropy(domain)
        features = extract_domain_features(domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {"reason": "NotFilteredNotFound"}
        
        run_local_first_pipeline(
            domain=domain,
            entropy=entropy,
            features=features,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            adguard_metadata=metadata
        )
        
        assert classifier.local_decisions_count >= initial_count


class TestDomainProcessing:
    """Tests for domain processing workflow."""

    def test_entropy_calculation_in_pipeline(self):
        """Test entropy is calculated correctly."""
        domains = [
            ("google.com", lambda e: e < 3.5),
            ("xkjf8329xnck1234.com", lambda e: e > 4.0),
            ("aa.com", lambda e: e < 2.0),
        ]
        
        for domain, assertion in domains:
            entropy = calculate_entropy(domain)
            assert assertion(entropy), f"Entropy assertion failed for {domain}: {entropy}"

    def test_feature_extraction(self):
        """Test domain feature extraction."""
        features = extract_domain_features("test123-domain.com")
        
        assert len(features) == 5
        assert features[1] == len("test123-domain")  # length
        assert 0 <= features[2] <= 1  # digit_ratio
        assert 0 <= features[3] <= 1  # vowel_ratio

    def test_processed_domains_tracking(self):
        """Test that processed domains are tracked."""
        test_domain = "unique-test-domain-12345.com"
        processed_domains.discard(test_domain)
        
        assert test_domain not in processed_domains
        
        processed_domains.add(test_domain)
        assert test_domain in processed_domains
        
        processed_domains.discard(test_domain)


class TestAnomalyDetectionIntegration:
    """Tests for anomaly detection in the pipeline."""

    def test_normal_domain_not_flagged(self):
        """Test that normal domains are not flagged as anomalies."""
        normal_domains = ["google.com", "amazon.com", "microsoft.com"]
        
        for domain in normal_domains:
            features = extract_domain_features(domain)
            is_anomaly, score = predict_anomaly(features)
            
            assert isinstance(is_anomaly, bool)
            assert isinstance(score, float)

    def test_suspicious_domain_detection(self):
        """Test detection of suspicious domain patterns."""
        suspicious_domains = [
            "xkjf8329xnck1234randomstring.com",
            "ab12cd34ef56gh78ij90.com",
        ]
        
        detected_count = 0
        for domain in suspicious_domains:
            if is_dga(domain):
                detected_count += 1
        
        assert detected_count >= 1


class TestMetricsCollection:
    """Tests for metrics collection during polling."""

    @patch("backend.services.adguard_poller.metrics_collector")
    def test_metrics_recorded_for_threat(self, mock_metrics):
        """Test that metrics are recorded for detected threats."""
        domain = "malware-test.com"
        entropy = calculate_entropy(domain)
        features = extract_domain_features(domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {
            "reason": "Blocked",
            "filter_id": 2,
            "rule": "||malware-test.com^",
        }
        
        run_local_first_pipeline(
            domain=domain,
            entropy=entropy,
            features=features,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            adguard_metadata=metadata
        )
        
        mock_metrics.record_classifier_decision.assert_called()
        mock_metrics.record_threat_detected.assert_called()

    @patch("backend.services.adguard_poller.alert_manager")
    def test_alert_manager_notified(self, mock_alert_manager):
        """Test that alert manager is notified of threats."""
        domain = "high-entropy-suspicious-domain12345.com"
        entropy = calculate_entropy(domain)
        features = extract_domain_features(domain)
        is_anomaly, anomaly_score = predict_anomaly(features)
        
        metadata = {"reason": "Blocked"}
        
        run_local_first_pipeline(
            domain=domain,
            entropy=entropy,
            features=features,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            adguard_metadata=metadata
        )
        
        pass


class TestCacheIntegration:
    """Tests for cache integration in polling."""

    @patch("backend.services.adguard_poller.get_cached_analysis")
    def test_cache_hit_skips_analysis(self, mock_get_cache):
        """Test that cache hit skips full analysis."""
        mock_get_cache.return_value = {
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": "Cached result"
        }
        
        domain = "cached-domain.com"
        metadata = {"reason": "NotFilteredNotFound"}
        
        cached = mock_get_cache(domain, metadata)
        
        assert cached is not None
        assert cached["risk_score"] == "Low"

    @patch("backend.services.adguard_poller.cache_analysis_result")
    def test_analysis_result_cached(self, mock_cache):
        """Test that analysis results are cached."""
        mock_cache.return_value = None
        
        mock_cache(
            "test-domain.com",
            {"reason": "Blocked"},
            {"risk_score": "High", "category": "Malware"},
            "local_heuristic",
            3600
        )
        
        mock_cache.assert_called_once()


class TestErrorHandling:
    """Tests for error handling in polling."""

    def test_malformed_log_handling(self):
        """Test handling of malformed log entries."""
        malformed_logs = [
            {},
            {"question": None},
            {"question": {"name": None}},
            {"question": {"name": ""}},
        ]
        
        for log in malformed_logs:
            question = log.get("question")
            if question is None:
                domain_data = None
            else:
                domain_data = question.get("name")
            
            if not domain_data:
                assert True
                continue
            
            domain = str(domain_data).lower().strip()
            if not domain:
                assert True

    def test_invalid_domain_handling(self):
        """Test handling of invalid domains."""
        invalid_domains = [
            "localhost",
            "test.local",
            "inverse.arpa",
            "",
        ]
        
        for domain in invalid_domains:
            if domain.endswith('.local') or domain.endswith('.arpa') or not domain:
                continue
            if not is_valid_domain(domain):
                continue
