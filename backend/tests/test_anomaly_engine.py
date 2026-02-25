import pytest
import numpy as np

from backend.logic.anomaly_engine import AnomalyEngine, engine


class TestAnomalyEngine:
    """Tests for the anomaly detection engine."""

    @pytest.fixture
    def fresh_engine(self):
        """Create a fresh anomaly engine for testing."""
        return AnomalyEngine(contamination=0.05, max_history=1000)

    def test_initial_state(self, fresh_engine):
        assert fresh_engine.is_trained is False
        assert len(fresh_engine.history) == 0
        assert fresh_engine.min_samples == 5

    def test_predict_anomaly_cold_start(self, fresh_engine):
        features = [3.5, 15, 0.1, 0.3, 1]

        is_anomaly, score = fresh_engine.predict_anomaly(features)

        assert is_anomaly is False
        assert score == 0.0

    def test_predict_anomaly_warmup(self, fresh_engine):
        for i in range(8):
            features = [3.0 + i * 0.1, 15 + i, 0.1, 0.3, 1]
            fresh_engine.predict_anomaly(features)

        assert len(fresh_engine.history) == 8

    def test_predict_anomaly_trained(self, fresh_engine):
        normal_features = [
            [2.5, 10, 0.0, 0.3, 0],
            [2.8, 12, 0.05, 0.35, 0],
            [3.0, 15, 0.1, 0.3, 1],
            [2.7, 11, 0.0, 0.32, 0],
            [2.9, 13, 0.08, 0.33, 1],
            [3.1, 14, 0.1, 0.31, 1],
            [2.6, 10, 0.0, 0.34, 0],
            [3.2, 16, 0.12, 0.3, 1],
            [2.8, 12, 0.05, 0.32, 0],
            [3.0, 15, 0.1, 0.3, 1],
            [2.7, 11, 0.0, 0.33, 0],
            [2.9, 13, 0.08, 0.34, 1],
        ]

        for f in normal_features:
            fresh_engine.predict_anomaly(f)

        assert fresh_engine.is_trained is True

        anomalous_features = [4.8, 45, 0.5, 0.1, 5]
        is_anomaly, score = fresh_engine.predict_anomaly(anomalous_features)

        assert isinstance(is_anomaly, bool)
        assert isinstance(score, float)

    def test_predict_anomaly_normal_domain(self, fresh_engine):
        for i in range(12):
            features = [3.0, 15, 0.1, 0.3, 1]
            fresh_engine.predict_anomaly(features)

        normal_features = [3.0, 14, 0.08, 0.32, 0]
        is_anomaly, score = fresh_engine.predict_anomaly(normal_features)

        assert isinstance(is_anomaly, bool)
        assert isinstance(score, float)

    def test_history_accumulation(self, fresh_engine):
        initial_count = len(fresh_engine.history)

        for i in range(5):
            features = [3.0 + i * 0.1, 15, 0.1, 0.3, 1]
            fresh_engine.predict_anomaly(features)

        assert len(fresh_engine.history) == initial_count + 5

    def test_max_history_limit(self):
        small_engine = AnomalyEngine(contamination=0.05, max_history=20)

        for i in range(30):
            features = [3.0 + i * 0.01, 15, 0.1, 0.3, 1]
            small_engine.predict_anomaly(features)

        assert len(small_engine.history) <= 20

    def test_get_stats(self, fresh_engine):
        stats = fresh_engine.get_stats()

        assert "is_trained" in stats
        assert "training_samples" in stats
        assert "min_samples_required" in stats
        assert "max_history_size" in stats
        assert "ready_for_prediction" in stats
        assert "contamination_rate" in stats

    def test_get_stats_after_training(self, fresh_engine):
        for i in range(12):
            features = [3.0, 15, 0.1, 0.3, 1]
            fresh_engine.predict_anomaly(features)

        stats = fresh_engine.get_stats()

        assert stats["is_trained"] is True
        assert stats["training_samples"] == 12
        assert stats["ready_for_prediction"] is True

    def test_score_range(self, fresh_engine):
        for i in range(12):
            features = [3.0, 15, 0.1, 0.3, 1]
            fresh_engine.predict_anomaly(features)

        test_features = [3.5, 20, 0.15, 0.28, 2]
        _, score = fresh_engine.predict_anomaly(test_features)

        assert -1.0 <= score <= 1.0

    def test_different_feature_sets(self, fresh_engine):
        feature_sets = [
            [2.0, 5, 0.0, 0.5, 0],
            [4.5, 30, 0.3, 0.1, 3],
            [3.0, 15, 0.1, 0.3, 1],
            [3.5, 20, 0.15, 0.25, 2],
            [2.5, 8, 0.05, 0.4, 0],
        ]

        for _ in range(3):
            for features in feature_sets:
                fresh_engine.predict_anomaly(features)

        assert fresh_engine.is_trained is True

    def test_global_engine_instance(self):
        from backend.logic.anomaly_engine import predict_anomaly, get_anomaly_stats

        stats = get_anomaly_stats()

        assert "is_trained" in stats
        assert "training_samples" in stats
