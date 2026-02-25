"""
Tests for the Feature Engineering system.
"""

import pytest
from datetime import datetime, UTC

from backend.logic.feature_engineering import (
    FeatureEngine,
    DomainFeatures,
    TemporalContext,
    HIGH_RISK_TLDS,
    LOW_RISK_TLDS,
)


@pytest.fixture
def feature_engine():
    return FeatureEngine(persistence_path="./data/test_features")


class TestDomainFeatures:
    def test_extract_features_basic(self, feature_engine):
        features = feature_engine.extract_features("example.com")

        assert features.tld == "com"
        assert features.length > 0
        assert features.entropy >= 0

    def test_extract_features_high_entropy(self, feature_engine):
        features = feature_engine.extract_features("asdfghjklqwert")

        assert features.entropy > 3.0

    def test_extract_features_digit_ratio(self, feature_engine):
        features = feature_engine.extract_features("test123456.com")

        assert features.digit_ratio > 0.3

    def test_extract_features_suspicious_keywords(self, feature_engine):
        features = feature_engine.extract_features("login-secure-bank.xyz")

        assert features.tld == "xyz"
        assert features.tld_reputation >= 0.7
        assert features.suspicious_keyword_score > 0

    def test_extract_features_brand_impersonation(self, feature_engine):
        features = feature_engine.extract_features("paypal-verify.com")

        assert features.brand_impersonation_risk > 0

    def test_extract_features_safe_domain(self, feature_engine):
        features = feature_engine.extract_features("google.com")

        assert features.brand_impersonation_risk == 0.0

    def test_extract_features_ip_address(self, feature_engine):
        features = feature_engine.extract_features("192.168.1.1")

        assert features.is_ip_address is True

    def test_extract_features_punycode(self, feature_engine):
        features = feature_engine.extract_features("xn--example.com")

        assert features.has_punycode is True

    def test_extract_features_hyphen_count(self, feature_engine):
        features = feature_engine.extract_features("a-b-c-d-e.com")

        assert features.hyphen_count >= 4

    def test_extract_features_www_prefix(self, feature_engine):
        features = feature_engine.extract_features("www.example.com")

        assert features.has_www is True


class TestTLDReputation:
    def test_high_risk_tld(self, feature_engine):
        features = feature_engine.extract_features("test.xyz")

        assert features.tld_reputation >= 0.8

    def test_low_risk_tld(self, feature_engine):
        features = feature_engine.extract_features("example.gov")

        assert features.tld_reputation <= 0.3

    def test_unknown_tld(self, feature_engine):
        features = feature_engine.extract_features("example.unknown")

        assert 0.3 <= features.tld_reputation <= 0.7

    def test_tld_stats_update(self, feature_engine):
        feature_engine.update_tld_stats("test", is_threat=True)
        feature_engine.update_tld_stats("test", is_threat=True)
        feature_engine.update_tld_stats("test", is_threat=False)

        report = feature_engine.get_tld_report()

        assert "test" in report["by_reputation"]


class TestTemporalContext:
    def test_temporal_context_basic(self, feature_engine):
        dt = datetime(2026, 2, 21, 14, 0, 0, tzinfo=UTC)
        context = feature_engine.get_temporal_context(dt)

        assert context.hour_of_day == 14
        assert context.day_of_week == 5
        assert context.is_business_hours is False
        assert context.is_weekend is True

    def test_temporal_context_night(self, feature_engine):
        dt = datetime(2026, 2, 21, 3, 0, 0, tzinfo=UTC)
        context = feature_engine.get_temporal_context(dt)

        assert context.hour_of_day == 3
        assert context.risk_multiplier == 1.3

    def test_temporal_context_business_hours(self, feature_engine):
        dt = datetime(2026, 2, 20, 10, 0, 0, tzinfo=UTC)
        context = feature_engine.get_temporal_context(dt)

        assert context.is_business_hours is True
        assert context.risk_multiplier == 0.9

    def test_temporal_stats_update(self, feature_engine):
        feature_engine.update_temporal_stats(hour=14, day=4, is_threat=True, risk_score=75.0)

        report = feature_engine.get_temporal_report()

        assert "peak_hours" in report
        assert "peak_days" in report


class TestEnhancedRiskScore:
    def test_risk_score_safe_domain(self, feature_engine):
        result = feature_engine.calculate_enhanced_risk_score("google.com")

        assert result["risk_score"] < 50
        assert result["risk_level"] == "Low"

    def test_risk_score_suspicious_domain(self, feature_engine):
        result = feature_engine.calculate_enhanced_risk_score("login-verify-paypal.xyz")

        assert result["risk_score"] > 40
        assert len(result["score_factors"]) > 0

    def test_risk_score_high_risk_tld(self, feature_engine):
        result = feature_engine.calculate_enhanced_risk_score("test.xyz")

        tld_factor = next(
            (f for f in result["score_factors"] if f["factor"] == "high_risk_tld"),
            None,
        )
        assert tld_factor is not None

    def test_risk_score_entropy_contribution(self, feature_engine):
        result = feature_engine.calculate_enhanced_risk_score("asdfghjklqwerty.xyz")

        entropy_factor = next(
            (f for f in result["score_factors"] if f["factor"] == "high_entropy"),
            None,
        )
        assert entropy_factor is not None

    def test_risk_score_brand_impersonation(self, feature_engine):
        result = feature_engine.calculate_enhanced_risk_score("google-secure.com")

        brand_factor = next(
            (f for f in result["score_factors"] if f["factor"] == "brand_impersonation"),
            None,
        )
        assert brand_factor is not None

    def test_risk_score_with_temporal_context(self, feature_engine):
        dt_night = datetime(2026, 2, 21, 3, 0, 0, tzinfo=UTC)
        dt_day = datetime(2026, 2, 20, 14, 0, 0, tzinfo=UTC)

        result_night = feature_engine.calculate_enhanced_risk_score(
            "test.com", temporal=feature_engine.get_temporal_context(dt_night)
        )
        result_day = feature_engine.calculate_enhanced_risk_score(
            "test.com", temporal=feature_engine.get_temporal_context(dt_day)
        )

        assert (
            result_night["temporal"]["risk_multiplier"] > result_day["temporal"]["risk_multiplier"]
        )

    def test_risk_score_structure(self, feature_engine):
        result = feature_engine.calculate_enhanced_risk_score("example.com")

        assert "domain" in result
        assert "risk_score" in result
        assert "risk_level" in result
        assert "score_factors" in result
        assert "features" in result
        assert "temporal" in result


class TestFeatureReports:
    def test_tld_report(self, feature_engine):
        report = feature_engine.get_tld_report()

        assert "tracked_tlds" in report
        assert "high_risk" in report
        assert "low_risk" in report
        assert "by_reputation" in report

    def test_temporal_report(self, feature_engine):
        report = feature_engine.get_temporal_report()

        assert "peak_hours" in report
        assert "peak_days" in report
        assert "hourly_breakdown" in report
