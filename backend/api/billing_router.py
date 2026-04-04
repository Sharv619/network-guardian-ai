"""
Billing and Subscription API Routes.

Provides endpoints for:
- Subscription management
- Stripe checkout and portal
- Webhooks handling
- Usage tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.core.deps import AuthenticatedUser, require_admin, require_authentication
from backend.services.billing_service import SubscriptionTier, billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


class SubscriptionInfo(BaseModel):
    tier: str
    name: str
    price_monthly: int
    price_yearly: int
    requests_per_day: int
    requests_per_minute: int
    features: list[str]


class PricingResponse(BaseModel):
    tiers: dict[str, SubscriptionInfo]
    current_tier: str = "free"


class CheckoutRequest(BaseModel):
    tier: str = Field(..., description="Subscription tier (pro or enterprise)")
    success_url: str = Field(..., description="URL to redirect on success")
    cancel_url: str = Field(..., description="URL to redirect on cancel")


class PortalRequest(BaseModel):
    return_url: str = Field(..., description="URL to return to after portal session")


class SubscriptionResponse(BaseModel):
    subscription_id: str
    customer_id: str
    status: str
    tier: str
    current_period_end: str
    cancel_at_period_end: bool


class UsageResponse(BaseModel):
    tenant_id: int
    period_start: str
    period_end: str
    domains_analyzed: int
    threats_detected: int
    daily_limit: int
    unlimited: bool


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing():
    """
    Get subscription pricing information.

    Returns pricing tiers without requiring authentication.
    """
    tiers = {}
    for tier_key, tier_config in SubscriptionTier.TIERS.items():
        tiers[tier_key] = SubscriptionInfo(
            tier=tier_key,
            name=tier_config["name"],
            price_monthly=tier_config["price_monthly"],
            price_yearly=tier_config["price_yearly"],
            requests_per_day=tier_config["requests_per_day"],
            requests_per_minute=tier_config["requests_per_minute"],
            features=tier_config["features"],
        )

    return PricingResponse(tiers=tiers)


@router.post("/create-customer")
async def create_stripe_customer(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Create a Stripe customer for the current tenant.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    tenant_name = getattr(request.state, "tenant_name", f"Tenant {tenant_id}")
    tenant_email = getattr(request.state, "tenant_email", f"tenant-{tenant_id}@example.com")

    try:
        result = billing_service.create_customer(
            email=tenant_email,
            name=tenant_name,
            tenant_id=tenant_id,
            metadata={"user": current_user.identity},
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create customer: {str(e)}",
        ) from e


@router.post("/checkout")
async def create_checkout_session(
    checkout: CheckoutRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Create a Stripe Checkout session for subscription upgrade.

    Requires authentication.
    """
    if checkout.tier not in [SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Must be 'pro' or 'enterprise'",
        )

    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    try:
        from backend.db.repository import TenantRepository

        repo = TenantRepository()
        await repo.update_stripe_customer_id(tenant_id, f"cus_tenant_{tenant_id}")

        session = billing_service.create_checkout_session(
            customer_id=f"cus_tenant_{tenant_id}",
            tier=checkout.tier,
            success_url=checkout.success_url,
            cancel_url=checkout.cancel_url,
        )
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}",
        ) from e


@router.post("/portal")
async def create_portal_session(
    portal: PortalRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Create a Stripe Customer Portal session.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    try:
        session = billing_service.create_portal_session(
            customer_id=f"cus_tenant_{tenant_id}",
            return_url=portal.return_url,
        )
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create portal session: {str(e)}",
        ) from e


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get usage statistics for the current tenant.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    period_start = now - timedelta(days=1)
    period_end = now

    usage = await billing_service.get_usage_for_tenant(tenant_id, period_start, period_end)

    return UsageResponse(**usage)


@router.get("/subscription")
async def get_subscription(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_authentication),
):
    """
    Get current subscription information.

    Requires authentication.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    try:
        from backend.db.repository import TenantRepository

        repo = TenantRepository()
        await repo.update_stripe_customer_id(tenant_id, f"cus_tenant_{tenant_id}")

        subscription = billing_service.get_subscription(f"sub_tenant_{tenant_id}")
        if subscription:
            return subscription
        return {
            "subscription_id": None,
            "customer_id": f"cus_tenant_{tenant_id}",
            "status": "none",
            "tier": "free",
            "current_period_end": None,
            "cancel_at_period_end": False,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription: {str(e)}",
        ) from e


@router.post("/cancel")
async def cancel_subscription(
    request: Request,
    immediately: bool = False,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Cancel the current subscription.

    Requires admin role.
    If immediately=True, cancels immediately. Otherwise, cancels at period end.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required",
        )

    try:
        result = billing_service.cancel_subscription(
            subscription_id=f"sub_tenant_{tenant_id}",
            immediately=immediately,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}",
        ) from e


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.

    This endpoint should be called by Stripe to notify about events.
    """
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = billing_service.config.webhook_secret

    try:
        event = billing_service.construct_webhook_event(payload, sig, webhook_secret)
        result = billing_service.handle_webhook_event(event)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook error: {str(e)}",
        ) from e


@router.get("/tiers")
async def get_tiers():
    """
    Get available subscription tiers.

    Returns tier information without requiring authentication.
    """
    return {
        "tiers": [
            {
                "id": tier_key,
                "name": config["name"],
                "price_monthly": config["price_monthly"],
                "price_yearly": config["price_yearly"],
                "features": config["features"],
            }
            for tier_key, config in SubscriptionTier.TIERS.items()
        ]
    }
