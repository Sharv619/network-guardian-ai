"""
Feedback Loop System for Continuous Learning.

This module provides:
- False positive/negative reporting
- Model retraining triggers
- Human-in-the-loop validation
- Continuous learning pipeline
"""

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.core.logging_config import get_logger
from backend.logic.metadata_classifier import classifier

logger = get_logger(__name__)

FEEDBACK_COOLDOWN = 300
MIN_FEEDBACK_FOR_RETRAIN = 10
RETRAIN_THRESHOLD_ACCURACY = 0.85


@dataclass
class FeedbackMetrics:
    """Track feedback metrics for the system."""

    total_feedback: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    correct_predictions: int = 0
    pending_retrain: bool = False
    last_retrain_time: str | None = None
    retrain_count: int = 0

    recent_feedback: deque = field(default_factory=lambda: deque(maxlen=100))


@dataclass
class FeedbackResult:
    """Result of processing feedback."""

    success: bool
    message: str
    triggered_retrain: bool = False
    metrics: dict[str, Any] | None = None


class FeedbackLoop:
    """Manages the feedback loop for continuous model improvement."""

    def __init__(self, persistence_path: Path = Path("./data/feedback")):
        self.persistence_path = persistence_path
        self.metrics = FeedbackMetrics()
        self._pending_corrections: list[dict[str, Any]] = []
        self._retrain_lock = asyncio.Lock()

        self._load_metrics()

    def record_feedback(
        self,
        domain: str,
        domain_id: int,
        feedback_type: str,
        original_category: str,
        original_risk: str,
        corrected_category: str | None = None,
        corrected_risk: str | None = None,
        user_note: str | None = None,
    ) -> FeedbackResult:
        """Record user feedback on a classification."""
        if feedback_type not in ["false_positive", "false_negative", "correct"]:
            return FeedbackResult(
                success=False,
                message=f"Invalid feedback type: {feedback_type}",
            )

        self.metrics.total_feedback += 1

        if feedback_type == "false_positive":
            self.metrics.false_positives += 1
        elif feedback_type == "false_negative":
            self.metrics.false_negatives += 1
        else:
            self.metrics.correct_predictions += 1

        feedback_entry = {
            "domain": domain,
            "domain_id": domain_id,
            "feedback_type": feedback_type,
            "original_category": original_category,
            "original_risk": original_risk,
            "corrected_category": corrected_category,
            "corrected_risk": corrected_risk,
            "user_note": user_note,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.metrics.recent_feedback.append(feedback_entry)

        if feedback_type in ["false_positive", "false_negative"] and corrected_category:
            self._pending_corrections.append(feedback_entry)

        self._save_metrics()

        triggered_retrain = self._check_retrain_trigger()

        accuracy = self._calculate_accuracy()

        return FeedbackResult(
            success=True,
            message=f"Feedback recorded. Current accuracy: {accuracy:.1%}",
            triggered_retrain=triggered_retrain,
            metrics=self.get_metrics(),
        )

    def _check_retrain_trigger(self) -> bool:
        """Check if we should trigger a model retrain."""
        total_classified = (
            self.metrics.false_positives
            + self.metrics.false_negatives
            + self.metrics.correct_predictions
        )

        if total_classified < MIN_FEEDBACK_FOR_RETRAIN:
            return False

        accuracy = self._calculate_accuracy()

        if accuracy < RETRAIN_THRESHOLD_ACCURACY and len(self._pending_corrections) >= 5:
            self.metrics.pending_retrain = True
            logger.warning(
                "Retrain triggered",
                extra={
                    "accuracy": accuracy,
                    "pending_corrections": len(self._pending_corrections),
                },
            )
            return True

        return False

    async def apply_corrections(self) -> dict[str, Any]:
        """Apply pending corrections to the classifier and thresholds."""
        async with self._retrain_lock:
            if not self._pending_corrections:
                return {"applied": 0, "message": "No pending corrections"}

            applied = 0
            for correction in self._pending_corrections:
                domain = correction["domain"]
                corrected_category = correction.get("corrected_category", "Unknown")

                classifier.learn_from_analysis(
                    domain=domain,
                    metadata={"reason": "User Correction", "rule": "manual_override"},
                    category=corrected_category,
                    system_used="feedback_loop",
                )
                applied += 1

            self._pending_corrections.clear()
            self.metrics.pending_retrain = False
            self.metrics.last_retrain_time = datetime.now(UTC).isoformat()
            self.metrics.retrain_count += 1

            self._save_metrics()

            logger.info(
                "Corrections applied",
                extra={"applied": applied, "retrain_count": self.metrics.retrain_count},
            )

            return {
                "applied": applied,
                "message": f"Applied {applied} corrections to the model",
                "retrain_count": self.metrics.retrain_count,
            }

    def _calculate_accuracy(self) -> float:
        """Calculate current model accuracy from feedback."""
        total = (
            self.metrics.false_positives
            + self.metrics.false_negatives
            + self.metrics.correct_predictions
        )
        if total == 0:
            return 1.0
        return self.metrics.correct_predictions / total

    def get_metrics(self) -> dict[str, Any]:
        """Get current feedback metrics."""
        return {
            "total_feedback": self.metrics.total_feedback,
            "false_positives": self.metrics.false_positives,
            "false_negatives": self.metrics.false_negatives,
            "correct_predictions": self.metrics.correct_predictions,
            "accuracy": self._calculate_accuracy(),
            "pending_retrain": self.metrics.pending_retrain,
            "last_retrain_time": self.metrics.last_retrain_time,
            "retrain_count": self.metrics.retrain_count,
            "pending_corrections": len(self._pending_corrections),
            "recent_feedback_count": len(self.metrics.recent_feedback),
        }

    def get_recent_feedback(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent feedback entries."""
        return list(self.metrics.recent_feedback)[-limit:]

    def _save_metrics(self) -> None:
        """Persist feedback metrics to disk."""
        try:
            self.persistence_path.mkdir(parents=True, exist_ok=True)

            data = {
                "total_feedback": self.metrics.total_feedback,
                "false_positives": self.metrics.false_positives,
                "false_negatives": self.metrics.false_negatives,
                "correct_predictions": self.metrics.correct_predictions,
                "last_retrain_time": self.metrics.last_retrain_time,
                "retrain_count": self.metrics.retrain_count,
                "recent_feedback": list(self.metrics.recent_feedback)[-50:],
            }

            path = self.persistence_path / "feedback_metrics.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error("Failed to save feedback metrics", extra={"error": str(e)})

    def _load_metrics(self) -> None:
        """Load persisted feedback metrics from disk."""
        try:
            path = self.persistence_path / "feedback_metrics.json"
            if not path.exists():
                return

            with open(path) as f:
                data = json.load(f)

            self.metrics.total_feedback = data.get("total_feedback", 0)
            self.metrics.false_positives = data.get("false_positives", 0)
            self.metrics.false_negatives = data.get("false_negatives", 0)
            self.metrics.correct_predictions = data.get("correct_predictions", 0)
            self.metrics.last_retrain_time = data.get("last_retrain_time")
            self.metrics.retrain_count = data.get("retrain_count", 0)

            for entry in data.get("recent_feedback", []):
                self.metrics.recent_feedback.append(entry)

            logger.info(
                "Loaded feedback metrics",
                extra={"total_feedback": self.metrics.total_feedback},
            )

        except Exception as e:
            logger.error("Failed to load feedback metrics", extra={"error": str(e)})


feedback_loop = FeedbackLoop()
