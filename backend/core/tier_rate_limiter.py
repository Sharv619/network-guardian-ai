"""
Tenant Rate Limiter Middleware.

Implements tier-based rate limiting for API requests.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class TierRateLimiter:
    """
    Rate limiter that enforces limits based on subscription tier.

    Limits:
    - Free: 10 requests/minute, 100 requests/day
    - Pro: 100 requests/minute, 10000 requests/day
    - Enterprise: Unlimited
    """

    def __init__(self) -> None:
        self._minute_requests: dict[int, list[float]] = defaultdict(list)
        self._day_requests: dict[int, list[float]] = defaultdict(list)
        self._tier_limits: dict[str, dict[str, int]] = {
            "free": {"per_minute": 10, "per_day": 100},
            "pro": {"per_minute": 100, "per_day": 10000},
            "enterprise": {"per_minute": -1, "per_day": -1},
        }
        self._lock = Lock()
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove old entries from tracking."""
        now = time.time()
        minute_ago = now - 60
        day_ago = now - 86400

        for tenant_id in list(self._minute_requests.keys()):
            self._minute_requests[tenant_id] = [
                t for t in self._minute_requests[tenant_id] if t > minute_ago
            ]
            if not self._minute_requests[tenant_id]:
                del self._minute_requests[tenant_id]

        for tenant_id in list(self._day_requests.keys()):
            self._day_requests[tenant_id] = [
                t for t in self._day_requests[tenant_id] if t > day_ago
            ]
            if not self._day_requests[tenant_id]:
                del self._day_requests[tenant_id]

    def check_rate_limit(self, tenant_id: int, tier: str) -> tuple[bool, dict[str, int]]:
        """
        Check if request is within rate limits.

        Returns:
            Tuple of (allowed, headers)
        """
        limits = self._tier_limits.get(tier, self._tier_limits["free"])

        if limits["per_minute"] == -1:
            return True, {
                "X-RateLimit-Limit": "-1",
                "X-RateLimit-Remaining": "-1",
            }

        now = time.time()
        minute_ago = now - 60

        with self._lock:
            self._minute_requests[tenant_id] = [
                t for t in self._minute_requests[tenant_id] if t > minute_ago
            ]
            self._day_requests[tenant_id] = [
                t for t in self._day_requests[tenant_id] if t > (now - 86400)
            ]

            minute_count = len(self._minute_requests[tenant_id])
            day_count = len(self._day_requests[tenant_id])

            if minute_count >= limits["per_minute"]:
                reset_time = int(self._minute_requests[tenant_id][0] + 60)
                return False, {
                    "X-RateLimit-Limit": str(limits["per_minute"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(int(self._minute_requests[tenant_id][0] + 60 - now)),
                }

            if limits["per_day"] > 0 and day_count >= limits["per_day"]:
                reset_time = int(self._day_requests[tenant_id][0] + 86400)
                return False, {
                    "X-RateLimit-Limit": str(limits["per_day"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(int(self._day_requests[tenant_id][0] + 86400 - now)),
                }

            self._minute_requests[tenant_id].append(now)
            self._day_requests[tenant_id].append(now)

            return True, {
                "X-RateLimit-Limit": str(limits["per_minute"]),
                "X-RateLimit-Remaining": str(limits["per_minute"] - minute_count - 1),
            }

    def get_usage(self, tenant_id: int, tier: str) -> dict[str, int]:
        """Get current usage for a tenant."""
        limits = self._tier_limits.get(tier, self._tier_limits["free"])
        now = time.time()
        minute_ago = now - 60

        with self._lock:
            minute_requests = [
                t for t in self._minute_requests.get(tenant_id, []) if t > minute_ago
            ]
            day_requests = [t for t in self._day_requests.get(tenant_id, []) if t > (now - 86400)]

            return {
                "requests_this_minute": len(minute_requests),
                "requests_today": len(day_requests),
                "minute_limit": limits["per_minute"],
                "day_limit": limits["per_day"],
            }


rate_limiter = TierRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces tier-based rate limiting.
    """

    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/billing/webhook",
        "/developer/endpoints",
    }

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        tier = getattr(request.state, "tier", "free")

        allowed, headers = rate_limiter.check_rate_limit(tenant_id, tier)

        if not allowed:
            return Response(
                status_code=429,
                content='{"detail": "Rate limit exceeded. Try again later."}',
                media_type="application/json",
                headers=headers,
            )

        response = await call_next(request)

        for key, value in headers.items():
            response.headers[key] = value

        return response
