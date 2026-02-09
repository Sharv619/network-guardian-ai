"""
Metadata Pattern Recognition System
Leverages AdGuard metadata to classify threats without Gemini API calls
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from ..core.utils import get_iso_timestamp
import hashlib

@dataclass
class MetadataPattern:
    """Represents a learned pattern from AdGuard metadata"""
    reason: str
    filter_id: Optional[int]
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
    pattern_id: Optional[str] = None

class MetadataClassifier:
    def __init__(self, pattern_db_path: str = "metadata_patterns.json"):
        self.pattern_db_path = pattern_db_path
        self.patterns: Dict[str, MetadataPattern] = {}
        self.pattern_counter = Counter()
        self.min_support = 3  # Minimum occurrences to create a pattern
        self.confidence_threshold = 0.8  # Minimum confidence for classification
        
        # Real-time metric tracking for demo
        self.local_decisions_count = 0
        self.cloud_decisions_count = 0
        self.total_patterns_learned = 0
        
        # Load existing patterns
        self.load_patterns()
        
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
                "source": "seed"
            },
            {
                "reason": "Processed", 
                "filter_id": 14,
                "rule": "||gstatic.com^",
                "category": "System", 
                "source": "seed"
            },
            # Microsoft Telemetry (Tracker)
            {
                "reason": "Blocked",
                "filter_id": 2,
                "rule": "||telemetry.microsoft.com^",
                "category": "Tracker",
                "source": "seed"
            },
            {
                "reason": "Blocked",
                "filter_id": 2, 
                "rule": "||settings-win.data.microsoft.com^",
                "category": "Tracker",
                "source": "seed"
            },
            # Malware DGA (Malware)
            {
                "reason": "Blocked",
                "filter_id": 1,
                "rule": "||*.xyz^",
                "category": "Malware",
                "source": "seed"
            }
        ]
        
        for pattern_data in seed_data:
            # Create pattern components
            reason = pattern_data["reason"]
            filter_id = pattern_data["filter_id"]
            rule_pattern = self._extract_rule_pattern(pattern_data["rule"])
            client_pattern = self._extract_client_pattern(None)  # No client for seed data
            
            # Create pattern key
            pattern_key = f"{reason}|{filter_id}|{rule_pattern}|{client_pattern}|{pattern_data['category']}"
            
            # Create pattern
            pattern = MetadataPattern(
                reason=reason,
                filter_id=filter_id,
                rule_pattern=rule_pattern,
                client_pattern=client_pattern,
                category=pattern_data["category"],
                confidence=0.95,  # High confidence for seed data
                support=100,  # Simulate learned from 100 examples
                last_seen=get_iso_timestamp()
            )
            
            pattern_id = self._generate_pattern_id(pattern)
            self.patterns[pattern_id] = pattern
            self.pattern_counter[pattern_key] = 100  # Simulate high support
        
        print(f"SEED INTELLIGENCE: Loaded {len(seed_data)} pre-learned patterns for immediate analysis")
    
    def load_patterns(self):
        """Load learned patterns from disk"""
        if os.path.exists(self.pattern_db_path):
            try:
                with open(self.pattern_db_path, 'r') as f:
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
            with open(self.pattern_db_path, 'w') as f:
                json.dump(pattern_data, f, indent=2)
        except Exception as e:
            print(f"Error saving patterns: {e}")
    
    def _generate_pattern_id(self, pattern: MetadataPattern) -> str:
        """Generate unique ID for a pattern"""
        pattern_str = f"{pattern.reason}|{pattern.filter_id}|{pattern.rule_pattern}|{pattern.client_pattern}"
        return hashlib.md5(pattern_str.encode()).hexdigest()[:8]
    
    def _extract_rule_pattern(self, rule: Optional[str]) -> str:
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
    
    def _extract_client_pattern(self, client: Optional[str]) -> str:
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
    
    def learn_from_analysis(self, domain: str, metadata: Dict, category: str, system_used: str = "gemini"):
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
        pattern_key = f"{reason}|{filter_id}|{rule_pattern}|{client_pattern}|{category}|{system_used}"
        
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
                last_seen=get_iso_timestamp()
            )
            
            pattern_id = self._generate_pattern_id(pattern)
            self.patterns[pattern_id] = pattern
            
            # Increment pattern learned counter
            self.increment_pattern_learned()
            
            print(f"🧠 PATTERN LEARNING: New {category} pattern learned from {system_used} analysis - {domain}")
            
            # Save patterns periodically
            if len(self.patterns) % 5 == 0:  # Save more frequently
                self.save_patterns()
    
    def classify(self, metadata: Dict) -> ClassificationResult:
        """Classify a domain based on metadata patterns"""
        reason = metadata.get("reason", "Unknown")
        filter_id = metadata.get("filter_id")
        rule_pattern = self._extract_rule_pattern(metadata.get("rule"))
        client_pattern = self._extract_client_pattern(metadata.get("client"))
        
        # Try to find matching patterns
        best_match = None
        best_confidence = 0
        
        for pattern_id, pattern in self.patterns.items():
            # Check for pattern match
            if (pattern.reason == reason and 
                pattern.rule_pattern == rule_pattern and
                (pattern.filter_id == filter_id or pattern.filter_id is None)):
                
                # Boost confidence if client pattern matches
                confidence = pattern.confidence
                if pattern.client_pattern == client_pattern:
                    confidence = min(confidence * 1.2, 1.0)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = pattern
        
        # Return classification if confidence is high enough
        if best_match and best_confidence >= self.confidence_threshold:
            return ClassificationResult(
                category=best_match.category,
                confidence=best_confidence,
                source="metadata_pattern",
                pattern_id=self._generate_pattern_id(best_match)
            )
        
        # Fallback to heuristic classification
        return self._heuristic_fallback(metadata)
    
    def _heuristic_fallback(self, metadata: Dict) -> ClassificationResult:
        """Fallback classification using metadata heuristics"""
        reason = metadata.get("reason", "")
        rule = metadata.get("rule", "").lower()
        
        # Heuristic rules based on AdGuard metadata
        if "tracking" in reason or "tracking" in rule:
            return ClassificationResult(
                category="Tracker",
                confidence=0.9,
                source="heuristic"
            )
        elif "malware" in reason or "malicious" in rule:
            return ClassificationResult(
                category="Malware",
                confidence=0.95,
                source="heuristic"
            )
        elif "privacy" in reason or any(kw in rule for kw in ["geo", "location", "gps"]):
            return ClassificationResult(
                category="Privacy Risk",
                confidence=0.85,
                source="heuristic"
            )
        elif "ads" in reason or "advertisement" in rule:
            return ClassificationResult(
                category="Advertisement",
                confidence=0.8,
                source="heuristic"
            )
        else:
            return ClassificationResult(
                category="Unknown",
                confidence=0.0,
                source="unknown"
            )
    
    def get_pattern_stats(self) -> Dict:
        """Get statistics about learned patterns"""
        category_counts = Counter()
        for pattern in self.patterns.values():
            category_counts[pattern.category] += 1
        
        return {
            "total_patterns": len(self.patterns),
            "category_distribution": dict(category_counts),
            "confidence_distribution": {
                "high": len([p for p in self.patterns.values() if p.confidence >= 0.9]),
                "medium": len([p for p in self.patterns.values() if 0.7 <= p.confidence < 0.9]),
                "low": len([p for p in self.patterns.values() if p.confidence < 0.7])
            }
        }
    
    def increment_local_decision(self):
        """Track when a domain is classified locally (without Gemini)"""
        self.local_decisions_count += 1
    
    def increment_cloud_decision(self):
        """Track when Gemini API is called"""
        self.cloud_decisions_count += 1
    
    def increment_pattern_learned(self):
        """Track when a new pattern is learned"""
        self.total_patterns_learned += 1
    
    def get_realtime_stats(self) -> Dict:
        """Get real-time metrics for the dashboard"""
        total_decisions = self.local_decisions_count + self.cloud_decisions_count
        autonomy_score = 0
        if total_decisions > 0:
            autonomy_score = (self.local_decisions_count / total_decisions) * 100
        
        return {
            "local_decisions": self.local_decisions_count,
            "cloud_decisions": self.cloud_decisions_count,
            "total_decisions": total_decisions,
            "autonomy_score": round(autonomy_score, 1),
            "patterns_learned": len(self.patterns) + self.total_patterns_learned,
            "seed_patterns": 5,  # We have 5 seed patterns
            "learned_patterns": len(self.patterns)  # Actual learned patterns
        }

# Global classifier instance
classifier = MetadataClassifier()

def classify_domain_metadata(metadata: Dict) -> ClassificationResult:
    """Public function to classify domain using metadata patterns"""
    return classifier.classify(metadata)

def learn_from_completed_analysis(domain: str, metadata: Dict, category: str):
    """Public function to learn from completed analysis"""
    classifier.learn_from_analysis(domain, metadata, category)

def get_classifier_stats() -> Dict:
    """Public function to get classifier statistics"""
    return classifier.get_pattern_stats()