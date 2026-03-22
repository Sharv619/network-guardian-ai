"""
Developer Portal API for Network Guardian AI.

Provides endpoints for:
- API key management for developers
- Usage analytics per API key
- Rate limit information
- Developer documentation access
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.deps import AuthenticatedUser, require_authentication
from backend.core.logging_config import get_logger
from backend.db.database import get_session
from backend.db.models import Tenant

logger = get_logger(__name__)

router = APIRouter(prefix="/developer", tags=["developer"])


class APIKeyInfo(BaseModel):
    name: str
    key_prefix: str
    created_at: str
    last_used: str | None
    is_active: bool
    request_count: int


class APIKeyListResponse(BaseModel):
    api_keys: list[APIKeyInfo]
    total: int


class GenerateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Name for the API key")
    expires_days: int = Field(365, ge=1, le=730, description="Days until key expires")


class GenerateAPIKeyResponse(BaseModel):
    api_key: str = Field(..., description="The API key (only shown once)")
    name: str
    expires_at: str
    message: str


class UsageByKeyResponse(BaseModel):
    api_key_name: str
    period_start: str
    period_end: str
    total_requests: int
    unique_domains: int
    threats_detected: int


class RateLimitInfo(BaseModel):
    tier: str
    requests_per_minute: int
    requests_per_day: int
    current_usage: int
    remaining: int
    reset_at: str


class DeveloperStatsResponse(BaseModel):
    tenant_id: int
    total_api_keys: int
    active_keys: int
    total_requests: int
    rate_limit: RateLimitInfo


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    List all API keys for the current tenant.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    from backend.core.auth import auth_credentials

    all_keys = auth_credentials.list_api_keys()

    return APIKeyListResponse(
        api_keys=[
            APIKeyInfo(
                name=key["name"],
                key_prefix="ng_****",
                created_at=key["created_at"],
                last_used=None,
                is_active=key["is_active"],
                request_count=0,
            )
            for key in all_keys
        ],
        total=len(all_keys),
    )


@router.post("/api-keys", response_model=GenerateAPIKeyResponse)
async def generate_api_key(
    key_request: GenerateAPIKeyRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Generate a new API key for the current tenant.

    The API key will be shown only once - save it immediately!

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    from backend.core.auth import APIKeyManager

    api_key = APIKeyManager.generate_api_key(prefix="ng")
    expires_at = datetime.now(UTC) + timedelta(days=key_request.expires_days)

    from backend.core.auth import auth_credentials

    auth_credentials.add_api_key(
        api_key=api_key,
        role="user",
        name=key_request.name,
        created_by=current_user.identity,
    )

    logger.info(
        f"API key generated: {key_request.name} for tenant {tenant_id}",
        extra={"tenant_id": tenant_id, "key_name": key_request.name},
    )

    return GenerateAPIKeyResponse(
        api_key=api_key,
        name=key_request.name,
        expires_at=expires_at.isoformat(),
        message="Save this API key - it won't be shown again!",
    )


@router.delete("/api-keys/{key_name}")
async def revoke_api_key(
    key_name: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Revoke an API key.

    Requires authentication.
    """
    from backend.core.auth import auth_credentials

    result = auth_credentials.revoke_api_key(key_name)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key '{key_name}' not found",
        )

    return {"message": f"API key '{key_name}' has been revoked"}


@router.get("/usage", response_model=list[UsageByKeyResponse])
async def get_usage_by_key(
    request: Request,
    days: int = Query(7, ge=1, le=30, description="Number of days to retrieve"),
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get usage statistics grouped by API key.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    from sqlalchemy import func

    from backend.db.models import Domain

    async with get_session() as session:
        start_date = datetime.now(UTC) - timedelta(days=days)

        query = select(
            func.count(Domain.id).label("total_requests"),
            func.count(func.distinct(Domain.domain)).label("unique_domains"),
            func.sum(func.case((Domain.risk_score.in_(["High", "Critical"]), 1), else_=0)).label(
                "threats"
            ),
        ).where(
            Domain.tenant_id == tenant_id,
            Domain.created_at >= start_date,
        )

        result = await session.execute(query)
        row = result.one()

        return [
            UsageByKeyResponse(
                api_key_name="All Keys",
                period_start=start_date.isoformat(),
                period_end=datetime.now(UTC).isoformat(),
                total_requests=row.total_requests or 0,
                unique_domains=row.unique_domains or 0,
                threats_detected=row.threats or 0,
            )
        ]


@router.get("/rate-limit", response_model=RateLimitInfo)
async def get_rate_limit_info(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get current rate limit information for the tenant.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    async with get_session() as session:
        result = await session.execute(
            select(Tenant.subscription_tier).where(Tenant.id == tenant_id)
        )
        row = result.scalar_one_or_none()
        tier = row or "free"

    from backend.services.billing_service import SubscriptionTier

    tier_config = SubscriptionTier.get_tier_config(tier)

    requests_per_minute = tier_config["requests_per_minute"]
    requests_per_day = tier_config["requests_per_day"]

    return RateLimitInfo(
        tier=tier,
        requests_per_minute=requests_per_minute if requests_per_minute != -1 else -1,
        requests_per_day=requests_per_day if requests_per_day != -1 else -1,
        current_usage=0,
        remaining=requests_per_minute if requests_per_minute != -1 else -1,
        reset_at=(datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
    )


@router.get("/stats", response_model=DeveloperStatsResponse)
async def get_developer_stats(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get developer statistics for the current tenant.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    from sqlalchemy import func

    from backend.core.auth import auth_credentials
    from backend.db.models import Domain

    all_keys = auth_credentials.list_api_keys()
    active_keys = sum(1 for k in all_keys if k.get("is_active", False))

    async with get_session() as session:
        count_query = select(func.count(Domain.id)).where(Domain.tenant_id == tenant_id)
        result = await session.execute(count_query)
        total_requests = result.scalar() or 0

    rate_limit = await get_rate_limit_info(request, current_user)

    return DeveloperStatsResponse(
        tenant_id=tenant_id,
        total_api_keys=len(all_keys),
        active_keys=active_keys,
        total_requests=total_requests,
        rate_limit=rate_limit,
    )


@router.get("/endpoints")
async def get_api_endpoints():
    """
    Get list of available API endpoints for developers.

    Public endpoint - no authentication required.
    """
    return {
        "base_url": "http://localhost:8000",
        "endpoints": [
            {
                "path": "/analyze",
                "method": "GET",
                "description": "Analyze a domain for threats",
                "params": [{"name": "domain", "type": "string", "required": True}],
            },
            {
                "path": "/history",
                "method": "GET",
                "description": "Get analysis history",
                "params": [
                    {"name": "page", "type": "int", "required": False},
                    {"name": "size", "type": "int", "required": False},
                ],
            },
            {
                "path": "/stats",
                "method": "GET",
                "description": "Get security statistics",
                "params": [],
            },
            {
                "path": "/chat",
                "method": "POST",
                "description": "Ask questions about threats",
                "body": {"message": "string", "required": True},
            },
            {
                "path": "/billing/pricing",
                "method": "GET",
                "description": "Get subscription pricing",
                "params": [],
            },
            {
                "path": "/developer/api-keys",
                "method": "POST",
                "description": "Generate new API key",
                "body": {"name": "string", "required": True},
            },
        ],
        "authentication": {
            "header": "X-Tenant-ID",
            "description": "Include tenant ID in all requests",
        },
    }
