import pytest

from backend.logic.metadata_classifier import (
    MetadataClassifier,
    ClassificationResult,
    classify_domain_metadata,
    learn_from_completed_analysis,
    get_classifier_stats,
)


class TestMetadataClassifier:
    """Tests for the metadata classifier."""

    @pytest.fixture
    def fresh_classifier(self, temp_cache_dir):
        """Create a fresh classifier with temporary pattern file."""
        import os
        pattern_file = os.path.join(temp_cache_dir, "test_patterns.json")
        return MetadataClassifier(pattern_db_path=pattern_file)

    def test_initial_state(self, fresh_classifier):
        assert fresh_classifier.local_decisions_count == 0
        assert fresh_classifier.cloud_decisions_count == 0
        assert fresh_classifier.confidence_threshold == 0.8

    def test_classify_blocked_malware(self, fresh_classifier):
        metadata = {
            "reason": "Blocked",
            "filter_id": 1,
            "rule": "||malware-site.com^",
            "client": "192.168.1.1",
        }

        result = fresh_classifier.classify(metadata)

        assert result.category is not None
        assert result.confidence >= 0.0

    def test_classify_blocked_tracking(self, fresh_classifier):
        metadata = {
            "reason": "Blocked",
            "filter_id": 2,
            "rule": "||tracking-analytics.com^",
            "client": "192.168.1.1",
        }

        result = fresh_classifier.classify(metadata)

        assert result.category is not None

    def test_classify_allowed_domain(self, fresh_classifier):
        metadata = {
            "reason": "NotFilteredNotFound",
            "filter_id": None,
            "rule": "",
            "client": "192.168.1.1",
        }

        result = fresh_classifier.classify(metadata)

        assert result is not None

    def test_classify_empty_metadata(self, fresh_classifier):
        result = fresh_classifier.classify({})

        assert result is not None
        assert result.source is not None

    def test_learn_from_analysis(self, fresh_classifier):
        initial_patterns = len(fresh_classifier.patterns)

        for _ in range(5):
            fresh_classifier.learn_from_analysis(
                domain="new-pattern.com",
                metadata={"reason": "Blocked", "filter_id": 3, "rule": "||blocked-domain.com^"},
                category="NewCategory",
                system_used="test",
            )

        assert fresh_classifier.pattern_counter["Blocked|3|BLOCK|UNKNOWN_CLIENT|NewCategory|test"] >= 3

    def test_learn_from_analysis_unknown_category(self, fresh_classifier):
        initial_patterns = len(fresh_classifier.patterns)

        fresh_classifier.learn_from_analysis(
            domain="unknown.com",
            metadata={"reason": "Processed"},
            category="Unknown",
        )

        assert len(fresh_classifier.patterns) == initial_patterns

    def test_learn_from_analysis_general_traffic(self, fresh_classifier):
        initial_patterns = len(fresh_classifier.patterns)

        fresh_classifier.learn_from_analysis(
            domain="example.com",
            metadata={"reason": "Processed"},
            category="General Traffic",
        )

        assert len(fresh_classifier.patterns) == initial_patterns

    def test_increment_local_decision(self, fresh_classifier):
        fresh_classifier.increment_local_decision()
        fresh_classifier.increment_local_decision()

        assert fresh_classifier.local_decisions_count == 2

    def test_increment_cloud_decision(self, fresh_classifier):
        fresh_classifier.increment_cloud_decision()
        fresh_classifier.increment_cloud_decision()
        fresh_classifier.increment_cloud_decision()

        assert fresh_classifier.cloud_decisions_count == 3

    def test_get_realtime_stats(self, fresh_classifier):
        fresh_classifier.increment_local_decision()
        fresh_classifier.increment_local_decision()
        fresh_classifier.increment_cloud_decision()

        stats = fresh_classifier.get_realtime_stats()

        assert stats["local_decisions"] == 2
        assert stats["cloud_decisions"] == 1
        assert stats["total_decisions"] == 3
        assert stats["autonomy_score"] == pytest.approx(66.67, rel=0.01)

    def test_get_realtime_stats_zero_decisions(self, fresh_classifier):
        stats = fresh_classifier.get_realtime_stats()

        assert stats["local_decisions"] == 0
        assert stats["cloud_decisions"] == 0
        assert stats["autonomy_score"] == 0

    def test_get_pattern_stats(self, fresh_classifier):
        stats = fresh_classifier.get_pattern_stats()

        assert "total_patterns" in stats
        assert "category_distribution" in stats
        assert "confidence_distribution" in stats

    def test_extract_rule_pattern_tracking(self, fresh_classifier):
        pattern = fresh_classifier._extract_rule_pattern("||tracking-analytics.com^")

        assert pattern == "TRACKING"

    def test_extract_rule_pattern_malware(self, fresh_classifier):
        pattern = fresh_classifier._extract_rule_pattern("||malware-domain.net^")

        assert pattern == "MALWARE"

    def test_extract_rule_pattern_privacy(self, fresh_classifier):
        pattern = fresh_classifier._extract_rule_pattern("||geo-location-service.com^")

        assert pattern == "PRIVACY"

    def test_extract_rule_pattern_ads(self, fresh_classifier):
        pattern = fresh_classifier._extract_rule_pattern("||ads-server.com^")

        assert pattern == "ADS"

    def test_extract_rule_pattern_empty(self, fresh_classifier):
        pattern = fresh_classifier._extract_rule_pattern("")

        assert pattern == "NO_RULE"

    def test_extract_client_pattern_mobile(self, fresh_classifier):
        pattern = fresh_classifier._extract_client_pattern("android-mobile-device")

        assert pattern == "MOBILE"

    def test_extract_client_pattern_desktop(self, fresh_classifier):
        pattern = fresh_classifier._extract_client_pattern("windows-desktop-pc")

        assert pattern == "DESKTOP"

    def test_extract_client_pattern_iot(self, fresh_classifier):
        pattern = fresh_classifier._extract_client_pattern("smart-tv-device")

        assert pattern == "IOT"

    def test_extract_client_pattern_unknown(self, fresh_classifier):
        pattern = fresh_classifier._extract_client_pattern(None)

        assert pattern == "UNKNOWN_CLIENT"

    def test_heuristic_fallback_tracking(self, fresh_classifier):
        metadata = {"reason": "tracking"}

        result = fresh_classifier._heuristic_fallback(metadata)

        assert result.category == "Tracker"
        assert result.confidence >= 0.8

    def test_heuristic_fallback_malware(self, fresh_classifier):
        metadata = {"reason": "malware", "rule": "malicious pattern"}

        result = fresh_classifier._heuristic_fallback(metadata)

        assert result.category == "Malware"

    def test_heuristic_fallback_privacy(self, fresh_classifier):
        metadata = {"reason": "privacy", "rule": "||geo-location.com^"}

        result = fresh_classifier._heuristic_fallback(metadata)

        assert result.category == "Privacy Risk"

    def test_heuristic_fallback_ads(self, fresh_classifier):
        metadata = {"reason": "ads", "rule": "||ads-network.com^"}

        result = fresh_classifier._heuristic_fallback(metadata)

        assert result.category == "Advertisement"

    def test_heuristic_fallback_unknown(self, fresh_classifier):
        metadata = {"reason": "unknown"}

        result = fresh_classifier._heuristic_fallback(metadata)

        assert result.category == "Unknown"
        assert result.confidence == 0.0

    def test_public_function_classify(self):
        result = classify_domain_metadata({"reason": "Blocked"})

        assert result is not None

    def test_public_function_get_stats(self):
        stats = get_classifier_stats()

        assert "total_patterns" in stats


class TestClassificationResult:
    """Tests for ClassificationResult dataclass."""

    def test_result_creation(self):
        result = ClassificationResult(
            category="Malware",
            confidence=0.95,
            source="heuristic",
            pattern_id="abc123",
        )

        assert result.category == "Malware"
        assert result.confidence == 0.95
        assert result.source == "heuristic"
        assert result.pattern_id == "abc123"

    def test_result_without_pattern_id(self):
        result = ClassificationResult(
            category="Tracker",
            confidence=0.8,
            source="metadata_pattern",
        )

        assert result.pattern_id is None
