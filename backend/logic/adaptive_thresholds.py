"""
Adaptive Thresholds for ML-based Threat Detection.

This module provides:
- Dynamic entropy thresholds based on historical data
- Context-aware scoring adjustments
- Statistical threshold adjustment
- Threshold history tracking for dashboard visualization
"""
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import json

from backend.core.config import settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_ENTROPY_THRESHOLD = 3.8
DEFAULT_CONTAMINATION_RATE = 0.05
MIN_SAMPLES_FOR_ADAPTATION = 100
ADAPTATION_WINDOW = 1000
PERCENTILE_HIGH = 95
PERCENTILE_LOW = 5


@dataclass
class ThresholdAdjustment:
    """Records a threshold adjustment event."""

    timestamp: str
    threshold_type: str
    old_value: float
    new_value: float
    reason: str
    samples_analyzed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "threshold_type": self.threshold_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "samples_analyzed": self.samples_analyzed,
        }


@dataclass
class AdaptiveThresholds:
    """Manages adaptive thresholds for threat detection."""

    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD
    contamination_rate: float = DEFAULT_CONTAMINATION_RATE

    entropy_history: deque = field(default_factory=lambda: deque(maxlen=ADAPTATION_WINDOW))
    anomaly_scores: deque = field(default_factory=lambda: deque(maxlen=ADAPTATION_WINDOW))

    adjustments: list[ThresholdAdjustment] = field(default_factory=list)

    last_adjustment_time: float = 0.0
    adjustment_cooldown: float = 3600.0

    _persistence_path: Path = field(default_factory=lambda: Path("./data/thresholds"))

    def __post_init__(self) -> None:
        self._load_persisted_data()

    def record_entropy(self, entropy: float) -> None:
        """Record an entropy value for threshold adaptation."""
        self.entropy_history.append(entropy)

        if len(self.entropy_history) >= MIN_SAMPLES_FOR_ADAPTATION:
            self._maybe_adjust_thresholds()

    def record_anomaly_score(self, score: float) -> None:
        """Record an anomaly score for contamination rate adaptation."""
        self.anomaly_scores.append(score)

    def get_entropy_threshold(self) -> float:
        """Get the current adaptive entropy threshold."""
        return self.entropy_threshold

    def get_contamination_rate(self) -> float:
        """Get the current adaptive contamination rate."""
        return self.contamination_rate

    def _maybe_adjust_thresholds(self) -> None:
        """Check if thresholds should be adjusted and do so."""
        current_time = time.time()

        if current_time - self.last_adjustment_time < self.adjustment_cooldown:
            return

        if len(self.entropy_history) < MIN_SAMPLES_FOR_ADAPTATION:
            return

        old_threshold = self.entropy_threshold
        history_list = list(self.entropy_history)

        p95 = self._percentile(history_list, PERCENTILE_HIGH)
        p5 = self._percentile(history_list, PERCENTILE_LOW)

        suggested_threshold = p95

        if abs(suggested_threshold - old_threshold) > 0.1:
            self.entropy_threshold = suggested_threshold
            self.last_adjustment_time = current_time

            adjustment = ThresholdAdjustment(
                timestamp=datetime.now(UTC).isoformat(),
                threshold_type="entropy",
                old_value=old_threshold,
                new_value=suggested_threshold,
                reason=f"Percentile-based adjustment (P95={p95:.2f}, P5={p5:.2f})",
                samples_analyzed=len(history_list),
            )
            self.adjustments.append(adjustment)
            self._persist()

            logger.info(
                "Entropy threshold adjusted",
                extra={
                    "old_threshold": old_threshold,
                    "new_threshold": suggested_threshold,
                    "samples_analyzed": len(history_list),
                }
            )

        self._adjust_contamination_rate()

    def _adjust_contamination_rate(self) -> None:
        """Adjust contamination rate based on anomaly score distribution."""
        if len(self.anomaly_scores) < MIN_SAMPLES_FOR_ADAPTATION:
            return

        scores = list(self.anomaly_scores)
        anomaly_count = sum(1 for s in scores if s < -0.1)
        observed_rate = anomaly_count / len(scores)

        target_rate = 0.05
        tolerance = 0.02

        if abs(observed_rate - target_rate) > tolerance:
            old_rate = self.contamination_rate

            if observed_rate > target_rate + tolerance:
                new_rate = min(0.15, self.contamination_rate + 0.01)
            elif observed_rate < target_rate - tolerance:
                new_rate = max(0.01, self.contamination_rate - 0.005)
            else:
                return

            self.contamination_rate = new_rate

            adjustment = ThresholdAdjustment(
                timestamp=datetime.now(UTC).isoformat(),
                threshold_type="contamination",
                old_value=old_rate,
                new_value=new_rate,
                reason=f"Observed anomaly rate: {observed_rate:.3f}, target: {target_rate}",
                samples_analyzed=len(scores),
            )
            self.adjustments.append(adjustment)
            self._persist()

            logger.info(
                "Contamination rate adjusted",
                extra={
                    "old_rate": old_rate,
                    "new_rate": new_rate,
                    "observed_rate": observed_rate,
                }
            )

    def _percentile(self, data: list[float], percentile: float) -> float:
        """Calculate percentile of a data list."""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]

    def get_context_multiplier(self, domain: str, hour: int | None = None) -> float:
        """
        Get a context-based multiplier for risk scoring.

        Args:
            domain: The domain being analyzed
            hour: Hour of day (0-23), defaults to current hour

        Returns:
            Multiplier (0.5 - 2.0) based on context
        """
        if hour is None:
            hour = datetime.now(UTC).hour

        multiplier = 1.0

        if 0 <= hour < 6:
            multiplier *= 1.3
        elif 9 <= hour <= 17:
            multiplier *= 0.9

        tld = self._extract_tld(domain)
        if tld in self._get_high_risk_tlds():
            multiplier *= 1.5
        elif tld in self._get_low_risk_tlds():
            multiplier *= 0.8

        return min(2.0, max(0.5, multiplier))

    def _extract_tld(self, domain: str) -> str:
        """Extract top-level domain from a domain name."""
        parts = domain.rsplit(".", 1)
        return parts[-1].lower() if len(parts) > 1 else ""

    def _get_high_risk_tlds(self) -> set[str]:
        """Get set of high-risk TLDs."""
        return {
            "xyz", "top", "click", "link", "work", "date", "racing",
            "stream", "gdn", "mom", "loan", "tk", "ml", "ga", "cf",
        }

    def _get_low_risk_tlds(self) -> set[str]:
        """Get set of low-risk TLDs."""
        return {
            "gov", "edu", "mil", "org", "ac", "int",
            "edu.au", "gov.uk", "ac.uk",
        }

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about adaptive thresholds."""
        history_list = list(self.entropy_history)

        return {
            "entropy_threshold": self.entropy_threshold,
            "contamination_rate": self.contamination_rate,
            "entropy_samples": len(history_list),
            "anomaly_samples": len(self.anomaly_scores),
            "adjustments_count": len(self.adjustments),
            "recent_adjustments": [
                adj.to_dict() for adj in self.adjustments[-5:]
            ],
            "entropy_distribution": {
                "min": min(history_list) if history_list else 0,
                "max": max(history_list) if history_list else 0,
                "mean": sum(history_list) / len(history_list) if history_list else 0,
                "p95": self._percentile(history_list, 95) if history_list else 0,
                "p5": self._percentile(history_list, 5) if history_list else 0,
            },
            "last_adjustment": (
                self.adjustments[-1].to_dict() if self.adjustments else None
            ),
        }

    def _persist(self) -> None:
        """Persist threshold state to disk."""
        try:
            self._persistence_path.mkdir(parents=True, exist_ok=True)

            data = {
                "entropy_threshold": self.entropy_threshold,
                "contamination_rate": self.contamination_rate,
                "adjustments": [adj.to_dict() for adj in self.adjustments[-100:]],
                "last_adjustment_time": self.last_adjustment_time,
            }

            path = self._persistence_path / "adaptive_thresholds.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error("Failed to persist thresholds", extra={"error": str(e)})

    def _load_persisted_data(self) -> None:
        """Load persisted threshold state from disk."""
        try:
            path = self._persistence_path / "adaptive_thresholds.json"
            if not path.exists():
                return

            with open(path, "r") as f:
                data = json.load(f)

            self.entropy_threshold = data.get("entropy_threshold", DEFAULT_ENTROPY_THRESHOLD)
            self.contamination_rate = data.get("contamination_rate", DEFAULT_CONTAMINATION_RATE)
            self.last_adjustment_time = data.get("last_adjustment_time", 0.0)

            for adj_data in data.get("adjustments", []):
                self.adjustments.append(ThresholdAdjustment(
                    timestamp=adj_data["timestamp"],
                    threshold_type=adj_data["threshold_type"],
                    old_value=adj_data["old_value"],
                    new_value=adj_data["new_value"],
                    reason=adj_data["reason"],
                    samples_analyzed=adj_data["samples_analyzed"],
                ))

            logger.info(
                "Loaded persisted thresholds",
                extra={
                    "entropy_threshold": self.entropy_threshold,
                    "contamination_rate": self.contamination_rate,
                }
            )

        except Exception as e:
            logger.error("Failed to load persisted thresholds", extra={"error": str(e)})


adaptive_thresholds = AdaptiveThresholds()
