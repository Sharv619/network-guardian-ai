"""
Tests for the Feedback Loop system.
"""

import pytest
from datetime import datetime, UTC

from backend.logic.feedback_loop import FeedbackLoop, FeedbackResult


@pytest.fixture
def feedback_loop():
    return FeedbackLoop(persistence_path="./data/test_feedback")


class TestFeedbackLoop:
    def test_record_false_positive(self, feedback_loop):
        result = feedback_loop.record_feedback(
            domain="example.com",
            domain_id=1,
            feedback_type="false_positive",
            original_category="Malware",
            original_risk="High",
            corrected_category="Safe",
            corrected_risk="Low",
        )

        assert result.success is True
        assert "false_positive" in result.message.lower() or "accuracy" in result.message.lower()

    def test_record_false_negative(self, feedback_loop):
        result = feedback_loop.record_feedback(
            domain="malicious.xyz",
            domain_id=2,
            feedback_type="false_negative",
            original_category="Safe",
            original_risk="Low",
            corrected_category="Malware",
            corrected_risk="High",
        )

        assert result.success is True

    def test_record_correct_prediction(self, feedback_loop):
        result = feedback_loop.record_feedback(
            domain="google.com",
            domain_id=3,
            feedback_type="correct",
            original_category="Safe",
            original_risk="Low",
        )

        assert result.success is True

    def test_invalid_feedback_type(self, feedback_loop):
        result = feedback_loop.record_feedback(
            domain="test.com",
            domain_id=4,
            feedback_type="invalid_type",
            original_category="Unknown",
            original_risk="Unknown",
        )

        assert result.success is False
        assert "invalid" in result.message.lower()

    def test_metrics_tracking(self, feedback_loop):
        feedback_loop.record_feedback(
            domain="test1.com",
            domain_id=1,
            feedback_type="false_positive",
            original_category="Malware",
            original_risk="High",
        )
        feedback_loop.record_feedback(
            domain="test2.com",
            domain_id=2,
            feedback_type="correct",
            original_category="Safe",
            original_risk="Low",
        )

        metrics = feedback_loop.get_metrics()

        assert metrics["total_feedback"] >= 2
        assert metrics["false_positives"] >= 1
        assert metrics["correct_predictions"] >= 1

    def test_accuracy_calculation(self, feedback_loop):
        for i in range(8):
            feedback_loop.record_feedback(
                domain=f"correct{i}.com",
                domain_id=i,
                feedback_type="correct",
                original_category="Safe",
                original_risk="Low",
            )

        for i in range(2):
            feedback_loop.record_feedback(
                domain=f"wrong{i}.com",
                domain_id=i + 10,
                feedback_type="false_positive",
                original_category="Malware",
                original_risk="High",
            )

        metrics = feedback_loop.get_metrics()

        assert metrics["accuracy"] == 0.8

    def test_retrain_trigger(self, feedback_loop):
        for i in range(10):
            feedback_loop.record_feedback(
                domain=f"fp{i}.com",
                domain_id=i,
                feedback_type="false_positive",
                original_category="Malware",
                original_risk="High",
                corrected_category="Safe",
                corrected_risk="Low",
            )

        metrics = feedback_loop.get_metrics()

        assert metrics["accuracy"] < 1.0
        assert len(feedback_loop._pending_corrections) == 10

    def test_get_recent_feedback(self, feedback_loop):
        for i in range(5):
            feedback_loop.record_feedback(
                domain=f"recent{i}.com",
                domain_id=i,
                feedback_type="correct",
                original_category="Safe",
                original_risk="Low",
            )

        recent = feedback_loop.get_recent_feedback(limit=3)

        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_apply_corrections(self, feedback_loop):
        feedback_loop.record_feedback(
            domain="correction.com",
            domain_id=1,
            feedback_type="false_positive",
            original_category="Malware",
            original_risk="High",
            corrected_category="Safe",
            corrected_risk="Low",
        )

        result = await feedback_loop.apply_corrections()

        assert result["applied"] >= 1
        assert feedback_loop.metrics.retrain_count >= 1


class TestFeedbackMetrics:
    def test_initial_state(self, feedback_loop):
        metrics = feedback_loop.get_metrics()

        assert metrics["total_feedback"] >= 0
        assert metrics["pending_retrain"] is False
        assert metrics["pending_corrections"] >= 0

    def test_metrics_structure(self, feedback_loop):
        metrics = feedback_loop.get_metrics()

        required_keys = [
            "total_feedback",
            "false_positives",
            "false_negatives",
            "correct_predictions",
            "accuracy",
            "pending_retrain",
            "last_retrain_time",
            "retrain_count",
            "pending_corrections",
            "recent_feedback_count",
        ]

        for key in required_keys:
            assert key in metrics
