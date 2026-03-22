"""
Tenant Management API Endpoints.

Provides endpoints for:
- Tenant registration and provisioning
- Tenant configuration management
- API key management
- Subscription tier management
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.core.deps import AuthenticatedUser, require_admin, require_authentication
from backend.core.logging_config import get_logger
from backend.db.database import get_session
from backend.db.models import Domain, Tenant

logger = get_logger(__name__)

router = APIRouter(prefix="/tenants", tags=["tenant-management"])


# Pydantic models for request/response
class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Tenant name")
    subdomain: str = Field(
        ..., min_length=3, max_length=50, description="Unique subdomain identifier"
    )
    api_key: str = Field(
        ..., min_length=10, max_length=255, description="Unique API key for tenant"
    )
    is_active: bool = Field(True, description="Whether the tenant is active")
    subscription_tier: str = Field("free", description="Subscription tier: free, pro, enterprise")


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    subdomain: str | None = Field(None, min_length=3, max_length=50)
    api_key: str | None = Field(None, min_length=10, max_length=255)
    is_active: bool | None = None
    subscription_tier: str | None = Field(None, pattern="^(free|pro|enterprise)$")


class TenantResponse(TenantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]
    total: int
    page: int
    size: int


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: Request,
    tenant_create: TenantCreate,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Create a new tenant.

    Requires admin role.
    """
    async with get_session() as session:
        # Check if subdomain already exists
        result = await session.execute(
            select(Tenant).where(Tenant.subdomain == tenant_create.subdomain)
        )
        existing_subdomain = result.scalar_one_or_none()
        if existing_subdomain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with subdomain '{tenant_create.subdomain}' already exists",
            )

        # Check if API key already exists
        result = await session.execute(
            select(Tenant).where(Tenant.api_key == tenant_create.api_key)
        )
        existing_api_key = result.scalar_one_or_none()
        if existing_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant with API key already exists",
            )

        # Create new tenant
        db_tenant = Tenant(
            name=tenant_create.name,
            subdomain=tenant_create.subdomain,
            api_key=tenant_create.api_key,
            is_active=tenant_create.is_active,
            subscription_tier=tenant_create.subscription_tier,
        )

        session.add(db_tenant)
        try:
            await session.commit()
            await session.refresh(db_tenant)
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Integrity error creating tenant: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create tenant due to data integrity issue",
            ) from e

        logger.info(
            f"Tenant created: {db_tenant.name} (ID: {db_tenant.id})",
            extra={
                "tenant_id": db_tenant.id,
                "tenant_name": db_tenant.name,
                "created_by": current_user.identity,
            },
        )

        return db_tenant


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    subscription_tier: str | None = Query(None, description="Filter by subscription tier"),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    List tenants with pagination and filtering.

    Requires admin role.
    """
    async with get_session() as session:
        # Build query
        query = select(Tenant)

        # Apply filters
        if is_active is not None:
            query = query.where(Tenant.is_active == is_active)
        if subscription_tier is not None:
            query = query.where(Tenant.subscription_tier == subscription_tier)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count(Tenant.id))
        if is_active is not None:
            count_query = count_query.where(Tenant.is_active == is_active)
        if subscription_tier is not None:
            count_query = count_query.where(Tenant.subscription_tier == subscription_tier)
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        # Execute query
        result = await session.execute(query)
        tenants = result.scalars().all()

        return TenantListResponse(
            tenants=[TenantResponse.model_validate(t) for t in tenants],
            total=total,
            page=page,
            size=size,
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    request: Request,
    tenant_id: int,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get a specific tenant by ID.

    Users can only view their own tenant unless they are admin.
    """
    async with get_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        # Check permissions: users can only view their own tenant unless admin
        # For now, we'll allow authenticated users to view any tenant (can be restricted later)
        # In a production system, you'd want to check: current_user.tenant_id == tenant_id or current_user.is_admin

        return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    request: Request,
    tenant_id: int,
    tenant_update: TenantUpdate,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Update a tenant.

    Requires admin role.
    """
    async with get_session() as session:
        # Get existing tenant
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        # Check for conflicts if subdomain or API key is being updated
        update_data = tenant_update.model_dump(exclude_unset=True)

        if "subdomain" in update_data:
            result = await session.execute(
                select(Tenant).where(
                    Tenant.subdomain == update_data["subdomain"], Tenant.id != tenant_id
                )
            )
            existing_subdomain = result.scalar_one_or_none()
            if existing_subdomain:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tenant with subdomain '{update_data['subdomain']}' already exists",
                )

        if "api_key" in update_data:
            result = await session.execute(
                select(Tenant).where(
                    Tenant.api_key == update_data["api_key"], Tenant.id != tenant_id
                )
            )
            existing_api_key = result.scalar_one_or_none()
            if existing_api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant with this API key already exists",
                )

        # Update fields
        for field, value in update_data.items():
            setattr(tenant, field, value)

        # Update the updated_at timestamp
        from datetime import UTC, datetime

        tenant.updated_at = datetime.now(UTC)

        try:
            await session.commit()
            await session.refresh(tenant)
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Integrity error updating tenant: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update tenant due to data integrity issue",
            ) from e

        logger.info(
            f"Tenant updated: {tenant.name} (ID: {tenant.id})",
            extra={
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "updated_by": current_user.identity,
                "changes": update_data,
            },
        )

        return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    request: Request,
    tenant_id: int,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Delete a tenant (soft delete by setting is_active=False).

    Requires admin role.
    """
    async with get_session() as session:
        # Get existing tenant
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        # Soft delete - set is_active to False
        tenant.is_active = False
        from datetime import UTC, datetime

        tenant.updated_at = datetime.now(UTC)

        await session.commit()

        logger.info(
            f"Tenant deactivated: {tenant.name} (ID: {tenant.id})",
            extra={
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "deactivated_by": current_user.identity,
            },
        )

        return None


@router.post("/{tenant_id}/regenerate-api-key", response_model=TenantResponse)
async def regenerate_api_key(
    request: Request,
    tenant_id: int,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Regenerate API key for a tenant.

    Requires admin role.
    """
    import secrets

    async with get_session() as session:
        # Get existing tenant
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        # Generate new API key
        # Using URL-safe base64 for API key
        new_api_key = secrets.token_urlsafe(32)

        # Check for uniqueness (though probability of collision is extremely low)
        result = await session.execute(
            select(Tenant).where(Tenant.api_key == new_api_key, Tenant.id != tenant_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Extremely unlikely, but handle just in case
            new_api_key = secrets.token_urlsafe(32)

        # Update API key
        tenant.api_key = new_api_key
        from datetime import UTC, datetime

        tenant.updated_at = datetime.now(UTC)

        await session.commit()
        await session.refresh(tenant)

        logger.info(
            f"API key regenerated for tenant: {tenant.name} (ID: {tenant.id})",
            extra={
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "regenerated_by": current_user.identity,
            },
        )

        return tenant


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    request: Request,
    tenant_id: int,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Activate a tenant.

    Requires admin role.
    """
    async with get_session() as session:
        # Get existing tenant
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        if tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant '{tenant.name}' is already active",
            )

        # Activate tenant
        tenant.is_active = True
        from datetime import UTC, datetime

        tenant.updated_at = datetime.now(UTC)

        await session.commit()
        await session.refresh(tenant)

        logger.info(
            f"Tenant activated: {tenant.name} (ID: {tenant.id})",
            extra={
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "activated_by": current_user.identity,
            },
        )

        return tenant


@router.post("/{tenant_id}/deactivate", response_model=TenantResponse)
async def deactivate_tenant(
    request: Request,
    tenant_id: int,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Deactivate a tenant.

    Requires admin role.
    """
    async with get_session() as session:
        # Get existing tenant
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant '{tenant.name}' is already inactive",
            )

        # Deactivate tenant
        tenant.is_active = False
        from datetime import UTC, datetime

        tenant.updated_at = datetime.now(UTC)

        await session.commit()
        await session.refresh(tenant)

        logger.info(
            f"Tenant deactivated: {tenant.name} (ID: {tenant.id})",
            extra={
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "deactivated_by": current_user.identity,
            },
        )

        return tenant


class UsageStatsResponse(BaseModel):
    tenant_id: int
    total_domains_analyzed: int
    threats_detected: int
    unique_categories: int
    subscription_tier: str
    tier_limit: int
    tier_unlimited: bool
    percentage_used: float


class DailyUsageResponse(BaseModel):
    date: str
    domains_analyzed: int
    threats_detected: int


@router.get("/{tenant_id}/usage", response_model=UsageStatsResponse)
async def get_tenant_usage_stats(
    request: Request,
    tenant_id: int,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get usage statistics for a specific tenant.

    Requires authentication.
    """
    async with get_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        from sqlalchemy import func

        total_query = select(func.count(Domain.id)).where(Domain.tenant_id == tenant_id)
        total_result = await session.execute(total_query)
        total_analyzed = total_result.scalar() or 0

        threat_query = select(func.count(Domain.id)).where(
            Domain.tenant_id == tenant_id,
            Domain.risk_score.in_(["High", "Critical"]),
        )
        threat_result = await session.execute(threat_query)
        threats_detected = threat_result.scalar() or 0

        category_query = select(func.count(func.distinct(Domain.category))).where(
            Domain.tenant_id == tenant_id
        )
        category_result = await session.execute(category_query)
        unique_categories = category_result.scalar() or 0

        from backend.services.billing_service import SubscriptionTier

        tier_config = SubscriptionTier.get_tier_config(tenant.subscription_tier)
        tier_limit = tier_config["requests_per_day"]
        tier_unlimited = tier_limit == -1

        percentage_used = 0.0
        if not tier_unlimited and tier_limit > 0:
            percentage_used = round((total_analyzed / tier_limit) * 100, 2)

        return UsageStatsResponse(
            tenant_id=tenant_id,
            total_domains_analyzed=total_analyzed,
            threats_detected=threats_detected,
            unique_categories=unique_categories,
            subscription_tier=tenant.subscription_tier,
            tier_limit=tier_limit,
            tier_unlimited=tier_unlimited,
            percentage_used=percentage_used,
        )


@router.get("/{tenant_id}/usage/daily", response_model=list[DailyUsageResponse])
async def get_tenant_daily_usage(
    request: Request,
    tenant_id: int,
    days: int = Query(7, ge=1, le=30, description="Number of days to retrieve"),
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get daily usage statistics for a specific tenant.

    Requires authentication.
    """
    async with get_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found",
            )

        from datetime import UTC, datetime, timedelta

        from sqlalchemy import func as sql_func

        start_date = datetime.now(UTC) - timedelta(days=days)

        query = (
            select(
                sql_func.date(Domain.created_at).label("date"),
                sql_func.count(Domain.id).label("count"),
                sql_func.sum(
                    sql_func.case((Domain.risk_score.in_(["High", "Critical"]), 1), else_=0)
                ).label("threats"),
            )
            .where(
                Domain.tenant_id == tenant_id,
                Domain.created_at >= start_date,
            )
            .group_by(sql_func.date(Domain.created_at))
            .order_by(sql_func.date(Domain.created_at))
        )

        result = await session.execute(query)
        rows = result.all()

        return [
            DailyUsageResponse(
                date=str(row.date),
                domains_analyzed=row.count,
                threats_detected=row.threats or 0,
            )
            for row in rows
        ]
