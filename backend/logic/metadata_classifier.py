"""
Metadata Pattern Recognition System
Leverages AdGuard metadata and blocklist data to classify threats without Gemini API calls
"""

import hashlib
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass

from ..core.utils import get_iso_timestamp

# Blocklist cache for fast lookups
_blocklist_cache: dict[str, dict] = {}
_blocklist_cache_loaded = False


def _load_blocklist_cache():
    """Load blocklist entries into memory cache for fast lookups."""
    global _blocklist_cache, _blocklist_cache_loaded
    if _blocklist_cache_loaded:
        return

        try:
            import asyncio

            from sqlalchemy import select

            from backend.db.database import get_session
            from backend.db.models import BlocklistEntry

            async def _load():
                async with get_session() as session:
                    result = await session.execute(select(BlocklistEntry).limit(500000))
                    entries = result.scalars().all()
                    for entry in entries:
                        _blocklist_cache[entry.domain] = {
                            "category": entry.category,
                            "source": entry.source,
                            "risk_level": entry.risk_level,
                        }
                    print(f"Blocklist cache loaded: {len(_blocklist_cache)} domains")

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(_load(), loop)
                future.result(timeout=30)
            except RuntimeError:
                asyncio.run(_load())
            _blocklist_cache_loaded = True
        except Exception as e:
            print(f"Warning: Could not load blocklist cache: {e}")


def check_blocklist(domain: str) -> dict | None:
    """Check if domain is in blocklist. Returns blocklist entry or None."""
    if not _blocklist_cache_loaded:
        _load_blocklist_cache()

    domain_lower = domain.lower()
    if domain_lower in _blocklist_cache:
        return _blocklist_cache[domain_lower]

    # Check for wildcard matches (e.g., subdomain of blocked domain)
    parts = domain_lower.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in _blocklist_cache:
            return _blocklist_cache[parent]

    return None


def invalidate_blocklist_cache():
    """Invalidate blocklist cache to force reload."""
    global _blocklist_cache, _blocklist_cache_loaded
    _blocklist_cache.clear()
    _blocklist_cache_loaded = False


@dataclass
class MetadataPattern:
    """Represents a learned pattern from AdGuard metadata"""

    reason: str
    filter_id: int | None
    rule_pattern: str
    client_pattern: str
    category: str
    confidence: float
    support: int
    last_seen: str


@dataclass
class ClassificationResult:
    """Result of metadata-based classification"""

    category: str
    confidence: float
    source: str  # "metadata_pattern", "heuristic", or "unknown"
    pattern_id: str | None = None


class MetadataClassifier:
    def __init__(self, pattern_db_path: str = "metadata_patterns.json"):
        self.pattern_db_path = pattern_db_path
        self.patterns: dict[str, MetadataPattern] = {}
        self.seed_patterns_count = 0  # Track seed patterns separately
        self.pattern_counter: Counter = Counter()
        self.min_support = 1  # Minimum occurrences to create a pattern (1 for demo)
        self.confidence_threshold = 0.8  # Minimum confidence for classification

        # Real-time metric tracking for demo
        self.local_decisions_count = 0
        self.cloud_decisions_count = 0
        self.total_patterns_learned = 0

        # Load existing patterns
        self.load_patterns()

        # Deferred: call async def init() from lifespan startup

    async def init(self):
        """Load persisted counters. Call from lifespan startup."""
        await self.load_stats()

        # Seed Intelligence: Pre-learned patterns for cold-start resilience
        self._seed_patterns()

    def _seed_patterns(self):
        """Seed the classifier with pre-learned patterns for immediate intelligence."""
        seed_data = [
            # Google Services (System)
            {
                "reason": "Processed",
                "filter_id": 14,
                "rule": "||googleapis.com^",
                "category": "System",
                "source": "seed",
            },
            {
                "reason": "Processed",
                "filter_id": 14,
                "rule": "||gstatic.com^",
                "category": "System",
                "source": "seed",
            },
            # Microsoft Telemetry (Tracker)
            {
                "reason": "Blocked",
                "filter_id": 2,
                "rule": "||telemetry.microsoft.com^",
                "category": "Tracker",
                "source": "seed",
            },
            {
                "reason": "Blocked",
                "filter_id": 2,
                "rule": "||settings-win.data.microsoft.com^",
                "category": "Tracker",
                "source": "seed",
            },
            # Malware DGA (Malware)
            {
                "reason": "Blocked",
                "filter_id": 1,
                "rule": "||*.xyz^",
                "category": "Malware",
                "source": "seed",
            },
        ]

        for pattern_data in seed_data:
            # Create pattern components
            reason = pattern_data["reason"]
            filter_id = pattern_data["filter_id"]
            rule_pattern = self._extract_rule_pattern(pattern_data["rule"])
            client_pattern = self._extract_client_pattern(None)  # No client for seed data

            # Create pattern key
            pattern_key = (
                f"{reason}|{filter_id}|{rule_pattern}|{client_pattern}|{pattern_data['category']}"
            )

            # Create pattern
            pattern = MetadataPattern(
                reason=reason,
                filter_id=filter_id,
                rule_pattern=rule_pattern,
                client_pattern=client_pattern,
                category=pattern_data["category"],
                confidence=0.95,  # High confidence for seed data
                support=100,  # Simulate learned from 100 examples
                last_seen=get_iso_timestamp(),
            )

            pattern_id = self._generate_pattern_id(pattern)
            self.patterns[pattern_id] = pattern
            self.pattern_counter[pattern_key] = 100  # Simulate high support

        self.seed_patterns_count = len(seed_data)
        print(
            f"SEED INTELLIGENCE: Loaded {len(seed_data)} pre-learned patterns for immediate analysis"
        )

    def load_patterns(self):
        """Load learned patterns from disk"""
        if os.path.exists(self.pattern_db_path):
            try:
                with open(self.pattern_db_path) as f:
                    data = json.load(f)
                    for pattern_data in data:
                        pattern = MetadataPattern(**pattern_data)
                        pattern_id = self._generate_pattern_id(pattern)
                        self.patterns[pattern_id] = pattern
                print(f"Loaded {len(self.patterns)} metadata patterns")
            except Exception as e:
                print(f"Error loading patterns: {e}")

    def save_patterns(self):
        """Save learned patterns to disk"""
        try:
            pattern_data = [asdict(pattern) for pattern in self.patterns.values()]
            with open(self.pattern_db_path, "w") as f:
                json.dump(pattern_data, f, indent=2)
        except Exception as e:
            print(f"Error saving patterns: {e}")

    def _generate_pattern_id(self, pattern: MetadataPattern) -> str:
        """Generate unique ID for a pattern"""
        pattern_str = (
            f"{pattern.reason}|{pattern.filter_id}|{pattern.rule_pattern}|{pattern.client_pattern}"
        )
        return hashlib.md5(pattern_str.encode()).hexdigest()[:8]

    def _extract_rule_pattern(self, rule: str | None) -> str:
        """Extract meaningful pattern from AdGuard rule"""
        if not rule:
            return "NO_RULE"

        # Normalize rule for pattern matching
        rule = rule.lower().strip()

        # Extract key indicators
        if "tracking" in rule or "telemetry" in rule:
            return "TRACKING"
        elif "malware" in rule or "malicious" in rule:
            return "MALWARE"
        elif "ads" in rule or "advertisement" in rule:
            return "ADS"
        elif "privacy" in rule or "geo" in rule or "location" in rule:
            return "PRIVACY"
        elif "social" in rule:
            return "SOCIAL"
        elif "analytics" in rule:
            return "ANALYTICS"
        elif "block" in rule:
            return "BLOCK"
        else:
            # Use first part of rule as pattern
            return rule.split()[0][:20] if rule else "GENERIC"

    def _extract_client_pattern(self, client: str | None) -> str:
        """Extract meaningful pattern from client info"""
        if not client:
            return "UNKNOWN_CLIENT"

        client = client.lower().strip()
        if "mobile" in client or "android" in client or "ios" in client:
            return "MOBILE"
        elif "desktop" in client or "windows" in client or "macos" in client:
            return "DESKTOP"
        elif "tv" in client or "smart" in client:
            return "IOT"
        else:
            return "OTHER_DEVICE"

    def learn_from_analysis(
        self, domain: str, metadata: dict, category: str, system_used: str = "ollama"
    ):
        """Learn from a completed analysis to build patterns"""
        # Only learn from high-confidence analyses
        if category in ["Unknown", "General Traffic"]:
            return

        # Extract pattern components
        reason = metadata.get("reason", "Unknown")
        filter_id = metadata.get("filter_id")
        rule_pattern = self._extract_rule_pattern(metadata.get("rule"))
        client_pattern = self._extract_client_pattern(metadata.get("client"))

        # Create pattern key with system information
        pattern_key = (
            f"{reason}|{filter_id}|{rule_pattern}|{client_pattern}|{category}|{system_used}"
        )

        # Count occurrences
        self.pattern_counter[pattern_key] += 1

        # Create pattern if we have enough support
        if self.pattern_counter[pattern_key] >= self.min_support:
            confidence = min(self.pattern_counter[pattern_key] / 10.0, 1.0)  # Cap confidence at 1.0

            pattern = MetadataPattern(
                reason=reason,
                filter_id=filter_id,
                rule_pattern=rule_pattern,
                client_pattern=client_pattern,
                category=category,
                confidence=confidence,
                support=self.pattern_counter[pattern_key],
                last_seen=get_iso_timestamp(),
            )

            pattern_id = self._generate_pattern_id(pattern)
            self.patterns[pattern_id] = pattern

            # Increment pattern learned counter
            self.increment_pattern_learned()

            print(
                f"🧠 PATTERN LEARNING: New {category} pattern learned from {system_used} analysis - {domain}"
            )

            # Save patterns periodically
            if len(self.patterns) % 5 == 0:  # Save more frequently
                self.save_patterns()

    def classify(self, metadata: dict, domain: str = "") -> ClassificationResult:
        """Classify a domain based on metadata patterns and blocklist"""
        # First, check blocklist for known threats
        if domain:
            blocklist_entry = check_blocklist(domain)
            if blocklist_entry:
                self.increment_local_decision()
                category = blocklist_entry.get("category", "General")
                confidence = 0.95
                return ClassificationResult(
                    category=category,
                    confidence=confidence,
                    source="blocklist",
                    pattern_id=None,
                )

        reason = metadata.get("reason", "Unknown")
        filter_id = metadata.get("filter_id")
        rule_pattern = self._extract_rule_pattern(metadata.get("rule"))
        client_pattern = self._extract_client_pattern(metadata.get("client"))

        # Try to find matching patterns
        best_match: MetadataPattern | None = None
        best_confidence = 0.0

        for _pattern_id, pattern in self.patterns.items():
            # Check for pattern match
            if (
                pattern.reason == reason
                and pattern.rule_pattern == rule_pattern
                and (pattern.filter_id == filter_id or pattern.filter_id is None)
            ):
                # Boost confidence if client pattern matches
                confidence = pattern.confidence
                if pattern.client_pattern == client_pattern:
                    confidence = min(confidence * 1.2, 1.0)

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = pattern

        # Return classification if confidence is high enough
        if best_match and best_confidence >= self.confidence_threshold:
            self.increment_local_decision()
            return ClassificationResult(
                category=best_match.category,
                confidence=best_confidence,
                source="metadata_pattern",
                pattern_id=self._generate_pattern_id(best_match),
            )

        # Fallback to heuristic classification
        return self._heuristic_fallback(metadata)

    def _heuristic_fallback(self, metadata: dict) -> ClassificationResult:
        """Fallback classification using metadata heuristics"""
        reason = metadata.get("reason", "")
        rule = metadata.get("rule", "").lower()

        # Heuristic rules based on AdGuard metadata
        if "tracking" in reason or "tracking" in rule:
            return ClassificationResult(category="Tracker", confidence=0.9, source="heuristic")
        elif "malware" in reason or "malicious" in rule:
            return ClassificationResult(category="Malware", confidence=0.95, source="heuristic")
        elif "privacy" in reason or any(kw in rule for kw in ["geo", "location", "gps"]):
            return ClassificationResult(
                category="Privacy Risk", confidence=0.85, source="heuristic"
            )
        elif "ads" in reason or "advertisement" in rule:
            return ClassificationResult(
                category="Advertisement", confidence=0.8, source="heuristic"
            )
        else:
            return ClassificationResult(category="Unknown", confidence=0.0, source="unknown")

    def get_pattern_stats(self) -> dict:
        """Get statistics about learned patterns"""
        category_counts: Counter = Counter()
        for pattern in self.patterns.values():
            category_counts[pattern.category] += 1

        return {
            "total_patterns": len(self.patterns),
            "category_distribution": dict(category_counts),
            "confidence_distribution": {
                "high": len([p for p in self.patterns.values() if p.confidence >= 0.9]),
                "medium": len([p for p in self.patterns.values() if 0.7 <= p.confidence < 0.9]),
                "low": len([p for p in self.patterns.values() if p.confidence < 0.7]),
            },
            "seed_patterns": self.seed_patterns_count,
        }

    def increment_local_decision(self):
        """Track when a domain is classified locally (without cloud AI)"""
        self.local_decisions_count += 1
        if self.local_decisions_count % 20 == 0:
            self._save_stats_async()

    def increment_cloud_decision(self):
        """Track when cloud AI is called"""
        self.cloud_decisions_count += 1
        if self.cloud_decisions_count % 20 == 0:
            self._save_stats_async()

    def increment_pattern_learned(self):
        """Track when a new pattern is learned"""
        self.total_patterns_learned += 1

    async def save_stats(self):
        """Persist counters to database."""
        from ..db.database import get_session
        from ..db.models import SystemStats
        from sqlalchemy import select

        try:
            async with get_session() as session:
                stats = {
                    "local_decisions_count": self.local_decisions_count,
                    "cloud_decisions_count": self.cloud_decisions_count,
                    "total_patterns_learned": self.total_patterns_learned,
                }
                for key, value in stats.items():
                    result = await session.execute(
                        select(SystemStats).where(
                            SystemStats.tenant_id == 1,
                            SystemStats.key == key,
                        )
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        existing.value = str(value)
                    else:
                        session.add(SystemStats(tenant_id=1, key=key, value=str(value)))
                await session.commit()
        except Exception as e:
            print(f"Warning: Could not save classifier stats: {e}")

    def _save_stats_async(self):
        """Non-blocking stats save."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.save_stats())
        except RuntimeError:
            # No running event loop — save will happen on next async call
            pass

    async def load_stats(self):
        """Load counters from database."""
        from ..db.database import get_session
        from ..db.models import SystemStats
        from sqlalchemy import select

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(SystemStats).where(SystemStats.tenant_id == 1)
                )
                for row in result.scalars().all():
                    if row.key == "local_decisions_count":
                        self.local_decisions_count = int(row.value)
                    elif row.key == "cloud_decisions_count":
                        self.cloud_decisions_count = int(row.value)
                    elif row.key == "total_patterns_learned":
                        self.total_patterns_learned = int(row.value)
        except Exception as e:
            print(f"Warning: Could not load classifier stats: {e}")

    def get_realtime_stats(self) -> dict:
        """Get real-time metrics for the dashboard"""
        total_decisions = self.local_decisions_count + self.cloud_decisions_count
        autonomy_score = 0.0
        if total_decisions > 0:
            autonomy_score = (self.local_decisions_count / total_decisions) * 100

        actual_learned = len(self.patterns) - self.seed_patterns_count

        return {
            "local_decisions": self.local_decisions_count,
            "cloud_decisions": self.cloud_decisions_count,
            "total_decisions": total_decisions,
            "autonomy_score": round(autonomy_score, 1),
            "patterns_learned": max(0, actual_learned),
            "seed_patterns": self.seed_patterns_count,
            "learned_patterns": max(0, actual_learned),
        }


# Global classifier instance
classifier = MetadataClassifier()


def classify_domain_metadata(metadata: dict, domain: str = "") -> ClassificationResult:
    """Public function to classify domain using metadata patterns and blocklist"""
    return classifier.classify(metadata, domain)


def learn_from_completed_analysis(domain: str, metadata: dict, category: str):
    """Public function to learn from completed analysis"""
    classifier.learn_from_analysis(domain, metadata, category)


def get_classifier_stats() -> dict:
    """Public function to get classifier statistics"""
    return classifier.get_pattern_stats()


def get_blocklist_stats() -> dict:
    """Get blocklist integration statistics"""
    return {
        "cache_loaded": _blocklist_cache_loaded,
        "cached_domains": len(_blocklist_cache),
        "sources_available": 4,
    }
