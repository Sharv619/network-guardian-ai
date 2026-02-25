import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitEntry:
    """Tracks rate limit state for a single key."""
    timestamps: list[float] = field(default_factory=list)
    blocked_until: Optional[float] = None


class RateLimiter:
    """
    Rate limiter with support for per-endpoint limits and burst allowance.
    
    Uses sliding window algorithm for accurate rate limiting.
    """

    def __init__(
        self,
        limit: int = 10,
        window: int = 60,
        burst: int = 0,
        prefix: str = "",
    ):
        self.limit = limit
        self.window = window
        self.burst = burst
        self.prefix = prefix
        self.requests: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

    def _get_key(self, identifier: str) -> str:
        """Construct the full rate limit key."""
        if self.prefix:
            return f"{self.prefix}:{identifier}"
        return identifier

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if a request is allowed for the given identifier.
        
        Args:
            identifier: The client identifier (e.g., IP address or user ID)
            
        Returns:
            True if allowed, False if rate limited
        """
        key = self._get_key(identifier)
        entry = self.requests[key]
        now = time.time()

        if entry.blocked_until and now < entry.blocked_until:
            logger.debug(
                "Request blocked (in cooldown)",
                extra={"key": key, "remaining": entry.blocked_until - now},
            )
            return False

        entry.timestamps = [
            ts for ts in entry.timestamps if now - ts < self.window
        ]

        effective_limit = self.limit + self.burst
        
        if len(entry.timestamps) >= effective_limit:
            logger.warning(
                "Rate limit exceeded",
                extra={"key": key, "requests": len(entry.timestamps), "limit": effective_limit},
            )
            return False

        entry.timestamps.append(now)
        return True

    def block(self, identifier: str, duration_seconds: int) -> None:
        """
        Block an identifier for a specified duration.
        
        Args:
            identifier: The client identifier to block
            duration_seconds: How long to block in seconds
        """
        key = self._get_key(identifier)
        entry = self.requests[key]
        entry.blocked_until = time.time() + duration_seconds
        
        logger.warning(
            "Identifier blocked",
            extra={"key": key, "duration_seconds": duration_seconds},
        )

    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for an identifier.
        
        Args:
            identifier: The client identifier
            
        Returns:
            Number of remaining requests in the current window
        """
        key = self._get_key(identifier)
        entry = self.requests[key]
        now = time.time()

        entry.timestamps = [
            ts for ts in entry.timestamps if now - ts < self.window
        ]

        effective_limit = self.limit + self.burst
        return max(0, effective_limit - len(entry.timestamps))

    def get_reset_time(self, identifier: str) -> Optional[float]:
        """
        Get the time when the rate limit will reset for an identifier.
        
        Args:
            identifier: The client identifier
            
        Returns:
            Unix timestamp when the limit resets, or None if not limited
        """
        key = self._get_key(identifier)
        entry = self.requests[key]
        
        if not entry.timestamps:
            return None

        return min(entry.timestamps) + self.window

    def clear(self, identifier: Optional[str] = None) -> None:
        """
        Clear rate limit state.
        
        Args:
            identifier: If provided, clear only this identifier. Otherwise clear all.
        """
        if identifier:
            key = self._get_key(identifier)
            if key in self.requests:
                del self.requests[key]
        else:
            self.requests.clear()

    def cleanup(self) -> int:
        """
        Remove expired entries to free memory.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        initial_count = len(self.requests)
        
        keys_to_remove = []
        for key, entry in self.requests.items():
            entry.timestamps = [ts for ts in entry.timestamps if now - ts < self.window]
            
            if not entry.timestamps and (not entry.blocked_until or entry.blocked_until < now):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.requests[key]

        removed = initial_count - len(self.requests)
        if removed > 0:
            logger.debug("Cleaned up rate limit entries", extra={"removed": removed})
        
        return removed


class MultiRateLimiter:
    """
    Manages multiple rate limiters for different endpoints.
    """

    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}

    def register(
        self,
        name: str,
        limit: int,
        window: int = 60,
        burst: int = 0,
    ) -> None:
        """Register a new rate limiter."""
        self.limiters[name] = RateLimiter(
            limit=limit,
            window=window,
            burst=burst,
            prefix=name,
        )
        logger.info("Rate limiter registered", extra={"limiter_name": name, "limit": limit, "window": window})

    def is_allowed(self, limiter_name: str, identifier: str) -> bool:
        """Check if a request is allowed for a specific limiter."""
        if limiter_name not in self.limiters:
            logger.warning("Unknown rate limiter", extra={"limiter_name": limiter_name})
            return True
        
        return self.limiters[limiter_name].is_allowed(identifier)

    def get_limiter(self, name: str) -> Optional[RateLimiter]:
        """Get a specific rate limiter."""
        return self.limiters.get(name)

    def cleanup_all(self) -> int:
        """Cleanup all rate limiters."""
        total_removed = 0
        for limiter in self.limiters.values():
            total_removed += limiter.cleanup()
        return total_removed


@dataclass
class IPReputationEntry:
    """Tracks reputation for a single IP address."""
    score: int = 0
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    violations: int = 0
    blocked: bool = False


class IPReputationTracker:
    """
    Tracks IP reputation based on behavior.
    
    Positive actions (successful requests) increase score.
    Negative actions (rate limit violations, blocked requests) decrease score.
    """

    def __init__(
        self,
        decay_hours: int = 24,
        block_threshold: int = -50,
        initial_score: int = 0,
    ):
        self.decay_hours = decay_hours
        self.block_threshold = block_threshold
        self.initial_score = initial_score
        self.reputations: Dict[str, IPReputationEntry] = {}

    def _apply_decay(self, entry: IPReputationEntry) -> None:
        """Apply time-based decay to reputation score."""
        now = datetime.now(timezone.utc)
        hours_elapsed = (now - entry.last_updated).total_seconds() / 3600

        if hours_elapsed >= 1:
            decay_factor = hours_elapsed / self.decay_hours
            if entry.score < self.initial_score:
                entry.score = min(
                    self.initial_score,
                    entry.score + int(10 * decay_factor),
                )
            elif entry.score > self.initial_score:
                entry.score = max(
                    self.initial_score,
                    entry.score - int(5 * decay_factor),
                )
            
            entry.last_updated = now

    def record_request(self, ip: str, success: bool = True) -> int:
        """
        Record a request and update reputation.
        
        Args:
            ip: The IP address
            success: Whether the request was successful
            
        Returns:
            The new reputation score
        """
        if ip not in self.reputations:
            self.reputations[ip] = IPReputationEntry(score=self.initial_score)

        entry = self.reputations[ip]
        self._apply_decay(entry)

        if success:
            entry.score = min(100, entry.score + 1)
        else:
            entry.score = max(-100, entry.score - 5)
            entry.violations += 1

        if entry.score <= self.block_threshold:
            entry.blocked = True
            logger.warning(
                "IP blocked due to low reputation",
                extra={"ip": ip, "score": entry.score},
            )

        return entry.score

    def record_rate_limit_violation(self, ip: str) -> int:
        """Record a rate limit violation."""
        return self.record_request(ip, success=False)

    def record_malicious_activity(self, ip: str, severity: int = 10) -> int:
        """
        Record malicious activity.
        
        Args:
            ip: The IP address
            severity: Severity of the activity (higher = more severe)
            
        Returns:
            The new reputation score
        """
        if ip not in self.reputations:
            self.reputations[ip] = IPReputationEntry(score=self.initial_score)

        entry = self.reputations[ip]
        self._apply_decay(entry)

        entry.score = max(-100, entry.score - severity)
        entry.violations += 1
        entry.blocked = entry.score <= self.block_threshold

        logger.warning(
            "Malicious activity recorded",
            extra={"ip": ip, "score": entry.score, "severity": severity},
        )

        return entry.score

    def get_score(self, ip: str) -> int:
        """Get the reputation score for an IP."""
        if ip not in self.reputations:
            return self.initial_score
        
        entry = self.reputations[ip]
        self._apply_decay(entry)
        return entry.score

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked."""
        if ip not in self.reputations:
            return False
        
        entry = self.reputations[ip]
        self._apply_decay(entry)
        
        if entry.blocked and entry.score > self.block_threshold + 10:
            entry.blocked = False
            logger.info("IP unblocked", extra={"ip": ip, "score": entry.score})
        
        return entry.blocked

    def block_ip(self, ip: str, reason: str = "manual") -> None:
        """Manually block an IP."""
        if ip not in self.reputations:
            self.reputations[ip] = IPReputationEntry(score=self.initial_score)

        entry = self.reputations[ip]
        entry.blocked = True
        entry.score = self.block_threshold - 10

        logger.warning(
            "IP manually blocked",
            extra={"ip": ip, "reason": reason, "score": entry.score},
        )

    def unblock_ip(self, ip: str) -> bool:
        """Manually unblock an IP."""
        if ip not in self.reputations:
            return False

        entry = self.reputations[ip]
        entry.blocked = False
        entry.score = self.initial_score

        logger.info("IP manually unblocked", extra={"ip": ip})
        return True

    def get_stats(self) -> dict:
        """Get reputation statistics."""
        total = len(self.reputations)
        blocked = sum(1 for e in self.reputations.values() if e.blocked)
        avg_score = sum(e.score for e in self.reputations.values()) / total if total > 0 else 0

        return {
            "total_ips_tracked": total,
            "blocked_ips": blocked,
            "average_score": round(avg_score, 2),
            "block_threshold": self.block_threshold,
        }

    def cleanup(self, max_age_hours: int = 168) -> int:
        """
        Remove old entries.
        
        Args:
            max_age_hours: Maximum age in hours (default 1 week)
            
        Returns:
            Number of entries removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        to_remove = [
            ip for ip, entry in self.reputations.items()
            if entry.last_updated < cutoff and not entry.blocked
        ]

        for ip in to_remove:
            del self.reputations[ip]

        if to_remove:
            logger.debug("Cleaned up reputation entries", extra={"removed": len(to_remove)})

        return len(to_remove)


multi_rate_limiter = MultiRateLimiter()
ip_reputation_tracker = IPReputationTracker()
