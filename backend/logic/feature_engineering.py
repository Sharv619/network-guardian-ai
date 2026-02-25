"""
Feature Engineering for Enhanced Domain Analysis.

This module provides:
- TLD reputation scoring based on historical data
- Temporal pattern analysis (time-based threat patterns)
- Additional domain features for ML pipeline
- Cross-reference with threat intelligence
"""

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.core.logging_config import get_logger

logger = get_logger(__name__)

HIGH_RISK_TLDS = {
    "xyz": 0.9,
    "top": 0.85,
    "click": 0.85,
    "link": 0.8,
    "work": 0.8,
    "date": 0.75,
    "racing": 0.85,
    "stream": 0.75,
    "gdn": 0.8,
    "mom": 0.7,
    "loan": 0.9,
    "tk": 0.9,
    "ml": 0.85,
    "ga": 0.85,
    "cf": 0.85,
    "gq": 0.85,
    "pw": 0.75,
    "cc": 0.7,
    "info": 0.5,
    "biz": 0.5,
}

LOW_RISK_TLDS = {
    "gov": 0.1,
    "edu": 0.15,
    "mil": 0.1,
    "org": 0.25,
    "ac": 0.2,
    "int": 0.15,
}

SUSPICIOUS_KEYWORDS = {
    "login": 0.7,
    "signin": 0.7,
    "account": 0.6,
    "verify": 0.65,
    "secure": 0.5,
    "update": 0.5,
    "confirm": 0.55,
    "password": 0.75,
    "bank": 0.7,
    "paypal": 0.8,
    "amazon": 0.7,
    "microsoft": 0.65,
    "google": 0.6,
    "apple": 0.65,
    "facebook": 0.6,
    "support": 0.5,
    "help": 0.4,
    "free": 0.55,
    "win": 0.7,
    "prize": 0.75,
    "crypto": 0.6,
    "wallet": 0.65,
}


@dataclass
class DomainFeatures:
    """Enhanced domain features for analysis."""

    tld: str
    tld_reputation: float
    length: int
    entropy: float
    digit_ratio: float
    vowel_ratio: float
    hyphen_count: int
    subdomain_count: int
    has_www: bool
    suspicious_keyword_score: float
    brand_impersonation_risk: float
    is_ip_address: bool
    has_punycode: bool


@dataclass
class TemporalContext:
    """Time-based context for analysis."""

    hour_of_day: int
    day_of_week: int
    is_business_hours: bool
    is_weekend: bool
    risk_multiplier: float
    historical_threat_rate: float


class FeatureEngine:
    """Enhanced feature extraction for domain analysis."""

    def __init__(self, persistence_path: Path = Path("./data/features")):
        self.persistence_path = persistence_path
        self._tld_stats: dict[str, dict[str, Any]] = {}
        self._temporal_stats: dict[str, dict[str, Any]] = {}
        self._hourly_patterns: dict[int, dict[str, Any]] = {}

        self._load_stats()

    def extract_features(self, domain: str) -> DomainFeatures:
        """Extract comprehensive features from a domain name."""
        domain_lower = domain.lower().strip()

        tld = self._extract_tld(domain_lower)
        main_part = self._extract_main_part(domain_lower)

        length = len(main_part)
        entropy = self._calculate_entropy(main_part)
        digit_ratio = sum(c.isdigit() for c in main_part) / max(length, 1)
        vowel_ratio = sum(c in "aeiou" for c in main_part) / max(length, 1)

        hyphen_count = domain_lower.count("-")
        subdomain_count = domain_lower.count(".")
        has_www = domain_lower.startswith("www.")
        has_punycode = "xn--" in domain_lower

        is_ip = self._is_ip_address(domain_lower)

        suspicious_score = self._calculate_suspicious_score(main_part)
        brand_risk = self._calculate_brand_impersonation_risk(domain_lower)

        tld_reputation = self._get_tld_reputation(tld)

        return DomainFeatures(
            tld=tld,
            tld_reputation=tld_reputation,
            length=length,
            entropy=entropy,
            digit_ratio=digit_ratio,
            vowel_ratio=vowel_ratio,
            hyphen_count=hyphen_count,
            subdomain_count=subdomain_count,
            has_www=has_www,
            suspicious_keyword_score=suspicious_score,
            brand_impersonation_risk=brand_risk,
            is_ip_address=is_ip,
            has_punycode=has_punycode,
        )

    def get_temporal_context(self, dt: datetime | None = None) -> TemporalContext:
        """Get temporal context for the given time (or now)."""
        if dt is None:
            dt = datetime.now(UTC)

        hour = dt.hour
        day = dt.weekday()

        is_business_hours = 9 <= hour <= 17 and day < 5
        is_weekend = day >= 5

        risk_multiplier = 1.0
        if 0 <= hour < 6:
            risk_multiplier = 1.3
        elif is_business_hours:
            risk_multiplier = 0.9
        elif 22 <= hour or hour < 2:
            risk_multiplier = 1.2

        historical_rate = self._get_historical_threat_rate(hour, day)

        return TemporalContext(
            hour_of_day=hour,
            day_of_week=day,
            is_business_hours=is_business_hours,
            is_weekend=is_weekend,
            risk_multiplier=risk_multiplier,
            historical_threat_rate=historical_rate,
        )

    def calculate_enhanced_risk_score(
        self,
        domain: str,
        features: DomainFeatures | None = None,
        temporal: TemporalContext | None = None,
    ) -> dict[str, Any]:
        """Calculate enhanced risk score with all features."""
        if features is None:
            features = self.extract_features(domain)
        if temporal is None:
            temporal = self.get_temporal_context()

        base_score = 0.0
        score_factors: list[dict[str, Any]] = []

        if features.tld_reputation >= 0.7:
            contribution = (features.tld_reputation - 0.5) * 20
            base_score += contribution
            score_factors.append(
                {"factor": "high_risk_tld", "contribution": contribution, "tld": features.tld}
            )
        elif features.tld_reputation <= 0.3:
            contribution = -(0.5 - features.tld_reputation) * 10
            base_score += contribution
            score_factors.append(
                {"factor": "low_risk_tld", "contribution": contribution, "tld": features.tld}
            )

        if features.entropy > 3.5:
            contribution = (features.entropy - 3.5) * 15
            base_score += contribution
            score_factors.append({"factor": "high_entropy", "contribution": contribution})

        if features.digit_ratio > 0.3:
            contribution = features.digit_ratio * 20
            base_score += contribution
            score_factors.append({"factor": "high_digit_ratio", "contribution": contribution})

        if features.hyphen_count > 2:
            contribution = features.hyphen_count * 5
            base_score += contribution
            score_factors.append({"factor": "many_hyphens", "contribution": contribution})

        if features.suspicious_keyword_score > 0:
            contribution = features.suspicious_keyword_score * 25
            base_score += contribution
            score_factors.append({"factor": "suspicious_keywords", "contribution": contribution})

        if features.brand_impersonation_risk > 0.5:
            contribution = features.brand_impersonation_risk * 30
            base_score += contribution
            score_factors.append({"factor": "brand_impersonation", "contribution": contribution})

        if features.is_ip_address:
            contribution = 25
            base_score += contribution
            score_factors.append({"factor": "ip_address_domain", "contribution": contribution})

        if features.has_punycode:
            contribution = 15
            base_score += contribution
            score_factors.append({"factor": "punycode_domain", "contribution": contribution})

        final_score = base_score * temporal.risk_multiplier

        final_score = max(0, min(100, final_score))

        if final_score >= 70:
            risk_level = "High"
        elif final_score >= 40:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return {
            "domain": domain,
            "risk_score": round(final_score, 1),
            "risk_level": risk_level,
            "score_factors": score_factors,
            "features": {
                "tld": features.tld,
                "tld_reputation": round(features.tld_reputation, 2),
                "entropy": round(features.entropy, 2),
                "digit_ratio": round(features.digit_ratio, 2),
                "suspicious_keyword_score": round(features.suspicious_keyword_score, 2),
                "brand_impersonation_risk": round(features.brand_impersonation_risk, 2),
            },
            "temporal": {
                "hour": temporal.hour_of_day,
                "day_of_week": temporal.day_of_week,
                "risk_multiplier": round(temporal.risk_multiplier, 2),
            },
        }

    def update_tld_stats(self, tld: str, is_threat: bool) -> None:
        """Update TLD statistics based on new data."""
        if tld not in self._tld_stats:
            self._tld_stats[tld] = {"threat_count": 0, "safe_count": 0}

        if is_threat:
            self._tld_stats[tld]["threat_count"] += 1
        else:
            self._tld_stats[tld]["safe_count"] += 1

        self._save_stats()

    def update_temporal_stats(
        self, hour: int, day: int, is_threat: bool, risk_score: float
    ) -> None:
        """Update temporal pattern statistics."""
        key = f"{hour}_{day}"
        if key not in self._temporal_stats:
            self._temporal_stats[key] = {
                "threat_count": 0,
                "total_count": 0,
                "risk_sum": 0.0,
            }

        self._temporal_stats[key]["total_count"] += 1
        self._temporal_stats[key]["risk_sum"] += risk_score
        if is_threat:
            self._temporal_stats[key]["threat_count"] += 1

        self._save_stats()

    def get_tld_report(self) -> dict[str, Any]:
        """Get report on TLD statistics."""
        report = {
            "tracked_tlds": len(self._tld_stats),
            "high_risk": [],
            "low_risk": [],
            "by_reputation": {},
        }

        for tld, stats in self._tld_stats.items():
            total = stats["threat_count"] + stats["safe_count"]
            if total == 0:
                continue

            threat_rate = stats["threat_count"] / total
            report["by_reputation"][tld] = {
                "threat_rate": round(threat_rate, 3),
                "total_seen": total,
            }

            if threat_rate > 0.5:
                report["high_risk"].append({"tld": tld, "threat_rate": round(threat_rate, 3)})
            elif threat_rate < 0.1:
                report["low_risk"].append({"tld": tld, "threat_rate": round(threat_rate, 3)})

        report["high_risk"].sort(key=lambda x: x["threat_rate"], reverse=True)
        report["low_risk"].sort(key=lambda x: x["threat_rate"])

        return report

    def get_temporal_report(self) -> dict[str, Any]:
        """Get report on temporal patterns."""
        hourly_data: dict[int, dict[str, Any]] = {}
        daily_data: dict[int, dict[str, Any]] = {}

        for key, stats in self._temporal_stats.items():
            hour, day = map(int, key.split("_"))
            total = stats["total_count"]

            if hour not in hourly_data:
                hourly_data[hour] = {"threat_count": 0, "total_count": 0, "avg_risk": 0.0}

            hourly_data[hour]["threat_count"] += stats["threat_count"]
            hourly_data[hour]["total_count"] += total

            if day not in daily_data:
                daily_data[day] = {"threat_count": 0, "total_count": 0}

            daily_data[day]["threat_count"] += stats["threat_count"]
            daily_data[day]["total_count"] += total

        peak_hours = sorted(
            [
                {"hour": h, "threat_rate": d["threat_count"] / max(d["total_count"], 1)}
                for h, d in hourly_data.items()
            ],
            key=lambda x: x["threat_rate"],
            reverse=True,
        )[:5]

        day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        peak_days = sorted(
            [
                {
                    "day": day_names[d],
                    "day_num": d,
                    "threat_rate": stats["threat_count"] / max(stats["total_count"], 1),
                }
                for d, stats in daily_data.items()
            ],
            key=lambda x: x["threat_rate"],
            reverse=True,
        )

        return {
            "peak_hours": peak_hours,
            "peak_days": peak_days,
            "hourly_breakdown": {
                h: {
                    "threat_rate": round(d["threat_count"] / max(d["total_count"], 1), 3),
                    "total": d["total_count"],
                }
                for h, d in hourly_data.items()
            },
        }

    def _extract_tld(self, domain: str) -> str:
        """Extract top-level domain."""
        parts = domain.rstrip("/").rsplit(".", 1)
        return parts[-1].lower() if len(parts) > 1 else ""

    def _extract_main_part(self, domain: str) -> str:
        """Extract main domain part (without TLD)."""
        domain = domain.lower()
        domain = domain.replace("https://", "").replace("http://", "")
        if domain.startswith("www."):
            domain = domain[4:]
        domain = domain.rstrip("/")

        parts = domain.split(".")
        return parts[0] if parts else domain

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0

        probs = [text.count(c) / len(text) for c in set(text)]
        return -sum(p * math.log2(p) for p in probs)

    def _is_ip_address(self, domain: str) -> bool:
        """Check if domain is an IP address."""
        parts = domain.replace("https://", "").replace("http://", "").split(".")
        if len(parts) != 4:
            return False

        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False

    def _calculate_suspicious_score(self, text: str) -> float:
        """Calculate score based on suspicious keywords."""
        text_lower = text.lower()
        max_score = 0.0

        for keyword, weight in SUSPICIOUS_KEYWORDS.items():
            if keyword in text_lower:
                max_score = max(max_score, weight)

        return max_score

    def _calculate_brand_impersonation_risk(self, domain: str) -> float:
        """Calculate risk of brand impersonation."""
        brands = [
            "google",
            "facebook",
            "amazon",
            "microsoft",
            "apple",
            "paypal",
            "netflix",
            "spotify",
            "twitter",
            "instagram",
            "linkedin",
            "dropbox",
            "adobe",
            "oracle",
            "ibm",
            "cisco",
        ]

        domain_lower = domain.lower()

        for brand in brands:
            if brand in domain_lower and not domain_lower.endswith(f".{brand}.com"):
                if domain_lower.startswith(f"{brand}-"):
                    return 0.85
                if f"-{brand}" in domain_lower:
                    return 0.9

        return 0.0

    def _get_tld_reputation(self, tld: str) -> float:
        """Get reputation score for TLD."""
        if tld in HIGH_RISK_TLDS:
            base = HIGH_RISK_TLDS[tld]
        elif tld in LOW_RISK_TLDS:
            base = LOW_RISK_TLDS[tld]
        else:
            base = 0.5

        if tld in self._tld_stats:
            stats = self._tld_stats[tld]
            total = stats["threat_count"] + stats["safe_count"]
            if total >= 5:
                observed_rate = stats["threat_count"] / total
                return (base + observed_rate) / 2

        return base

    def _get_historical_threat_rate(self, hour: int, day: int) -> float:
        """Get historical threat rate for time slot."""
        key = f"{hour}_{day}"
        if key in self._temporal_stats:
            stats = self._temporal_stats[key]
            if stats["total_count"] > 0:
                return stats["threat_count"] / stats["total_count"]
        return 0.05

    def _save_stats(self) -> None:
        """Persist feature stats to disk."""
        try:
            self.persistence_path.mkdir(parents=True, exist_ok=True)

            data = {
                "tld_stats": self._tld_stats,
                "temporal_stats": self._temporal_stats,
            }

            path = self.persistence_path / "feature_stats.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error("Failed to save feature stats", extra={"error": str(e)})

    def _load_stats(self) -> None:
        """Load persisted feature stats from disk."""
        try:
            path = self.persistence_path / "feature_stats.json"
            if not path.exists():
                return

            with open(path) as f:
                data = json.load(f)

            self._tld_stats = data.get("tld_stats", {})
            self._temporal_stats = data.get("temporal_stats", {})

            logger.info(
                "Loaded feature stats",
                extra={
                    "tld_count": len(self._tld_stats),
                    "temporal_count": len(self._temporal_stats),
                },
            )

        except Exception as e:
            logger.error("Failed to load feature stats", extra={"error": str(e)})


feature_engine = FeatureEngine()
