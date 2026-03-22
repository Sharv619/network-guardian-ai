import json
import logging
import time

from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..db.database import get_session
from ..db.models import Tenant
from ..db.repository import get_domain_repository

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant information from requests and inject it into the request state.
    Supports multiple methods of tenant identification:
    1. Subdomain (e.g., tenant1.app.domain.com)
    2. Custom header (X-Tenant-ID or X-Tenant-API-Key)
    3. API key in query parameter (?api_key=...)
    4. JWT token (future enhancement)
    """

    def __init__(self, app, exclude_paths: list | None = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/models",
            "/metrics",
            "/assets",
            "/vite.svg",
            "/ws",
            "/billing/pricing",
            "/billing/tiers",
            "/billing/webhook",
            "/auth/register",
            "/auth/tiers",
            "/developer/endpoints",
        ]
        # Cache for tenant lookups: {key: (tenant_id, expiry_time)}
        self._subdomain_cache: dict[str, tuple[int, float]] = {}
        self._api_key_cache: dict[str, tuple[int, float]] = {}
        self._cache_timeout = 300  # 5 minutes

    async def dispatch(self, request: Request, call_next):
        # Skip tenant identification for excluded paths (supports prefix matching)
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Extract tenant information
        tenant_id = await self._extract_tenant_id(request)

        if tenant_id is None:
            logger.warning(
                "Tenant identification failed",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "host": request.url.hostname,
                },
            )
            return Response(
                status_code=401,
                content=json.dumps({"detail": "Tenant identification required"}),
                media_type="application/json",
            )

        # Inject tenant_id into request state for use in endpoints
        request.state.tenant_id = tenant_id

        # Also inject the tenant repository for convenience
        request.state.tenant_repo = await get_domain_repository(tenant_id=tenant_id)

        response = await call_next(request)
        return response

    async def _extract_tenant_id(self, request: Request) -> int | None:
        """
        Extract tenant ID from the request using various methods.
        Returns the tenant ID if found, None otherwise.
        Uses caching to avoid repeated database lookups.
        """
        # Method 1: Subdomain extraction
        # Format: tenant1.app.domain.com -> tenant1
        host = request.url.hostname or ""
        if host and "." in host:
            subdomain = host.split(".")[0]
            if subdomain not in ["www", "app", "api", "localhost"]:
                # Look up tenant by subdomain with caching
                cached = self._subdomain_cache.get(subdomain)
                if cached and cached[1] > time.time():
                    return cached[0]
                # Cache miss or expired, query database
                try:
                    async with get_session() as session:
                        result = await session.execute(
                            select(Tenant.id).where(Tenant.subdomain == subdomain, Tenant.is_active)
                        )
                        tenant_id_val = result.scalar_one_or_none()
                        if tenant_id_val is not None:
                            tenant_id = tenant_id_val
                            # Update cache
                            self._subdomain_cache[subdomain] = (
                                tenant_id,
                                time.time() + self._cache_timeout,
                            )
                            logger.debug(
                                f"Tenant found by subdomain: {subdomain} -> {tenant_id}",
                                extra={"subdomain": subdomain, "tenant_id": tenant_id},
                            )
                            return tenant_id
                except Exception as e:
                    logger.error(
                        f"Database error while looking up tenant by subdomain {subdomain}: {e}",
                        extra={"subdomain": subdomain},
                        exc_info=True,
                    )
                    # Continue to other methods

        # Method 2: Custom headers
        tenant_id_header = request.headers.get("X-Tenant-ID")
        if tenant_id_header:
            try:
                tenant_id = int(tenant_id_header)
                # Validate that the tenant exists and is active
                async with get_session() as session:
                    result = await session.execute(
                        select(Tenant.id).where(Tenant.id == tenant_id, Tenant.is_active)
                    )
                    tenant_id_val = result.scalar_one_or_none()
                    if tenant_id_val is not None:
                        logger.debug(
                            f"Tenant found by X-Tenant-ID header: {tenant_id}",
                            extra={"tenant_id": tenant_id},
                        )
                        return tenant_id
                    else:
                        logger.warning(
                            f"Tenant ID {tenant_id} from header not found or inactive",
                            extra={"tenant_id": tenant_id},
                        )
            except ValueError:
                logger.warning(
                    f"Invalid X-Tenant-ID header value: {tenant_id_header}",
                    extra={"tenant_id_header": tenant_id_header},
                )
            except Exception as e:
                logger.error(
                    f"Database error while validating tenant ID {tenant_id_header}: {e}",
                    extra={"tenant_id_header": tenant_id_header},
                    exc_info=True,
                )

        api_key_header = request.headers.get("X-Tenant-API-Key")
        if api_key_header:
            # Look up by API key with caching
            cached = self._api_key_cache.get(api_key_header)
            if cached and cached[1] > time.time():
                return cached[0]
            try:
                async with get_session() as session:
                    result = await session.execute(
                        select(Tenant.id).where(Tenant.api_key == api_key_header, Tenant.is_active)
                    )
                    tenant_id_val = result.scalar_one_or_none()
                    if tenant_id_val is not None:
                        tenant_id = tenant_id_val
                        # Update cache
                        self._api_key_cache[api_key_header] = (
                            tenant_id,
                            time.time() + self._cache_timeout,
                        )
                        logger.debug(
                            f"Tenant found by X-Tenant-API-Key header: {tenant_id}",
                            extra={"tenant_id": tenant_id},
                        )
                        return tenant_id
            except Exception as e:
                logger.error(
                    f"Database error while looking up tenant by API key header: {e}",
                    extra={"api_key_header": api_key_header},
                    exc_info=True,
                )

        # Method 3: Query parameter
        api_key_param = request.query_params.get("api_key")
        if api_key_param:
            # Look up by API key with caching
            cached = self._api_key_cache.get(api_key_param)
            if cached and cached[1] > time.time():
                return cached[0]
            try:
                async with get_session() as session:
                    result = await session.execute(
                        select(Tenant.id).where(Tenant.api_key == api_key_param, Tenant.is_active)
                    )
                    tenant_id_val = result.scalar_one_or_none()
                    if tenant_id_val is not None:
                        tenant_id = tenant_id_val
                        # Update cache
                        self._api_key_cache[api_key_param] = (
                            tenant_id,
                            time.time() + self._cache_timeout,
                        )
                        logger.debug(
                            f"Tenant found by api_key query param: {tenant_id}",
                            extra={"api_key_param": api_key_param, "tenant_id": tenant_id},
                        )
                        return tenant_id
            except Exception as e:
                logger.error(
                    f"Database error while looking up tenant by API key query param: {e}",
                    extra={"api_key_param": api_key_param},
                    exc_info=True,
                )

        # Method 4: Default tenant for development/testing
        # In production, this should be removed or disabled
        # We'll check if the environment is set to development via an environment variable
        import os

        if os.getenv("ENVIRONMENT", "production").lower() == "development":
            # Return a default tenant ID (1) for development
            logger.warning(
                "Using default tenant ID (1) for development environment",
                extra={"environment": os.getenv("ENVIRONMENT")},
            )
            return 1

        return None
