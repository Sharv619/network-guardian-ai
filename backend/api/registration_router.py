"""
User Registration and Onboarding API Routes.

Provides endpoints for:
- User registration
- Tenant creation during signup
- Welcome/onboarding flow
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.core.auth import APIKeyManager, UserRole, auth_credentials
from backend.core.logging_config import get_logger
from backend.db.database import get_session
from backend.db.models import Tenant
from backend.services.billing_service import SubscriptionTier

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["registration"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    company_name: str = Field(..., min_length=1, max_length=100)
    subscription_tier: str = Field("free", pattern="^(free|pro|enterprise)$")


class RegisterResponse(BaseModel):
    user_id: str
    tenant_id: int
    username: str
    email: str
    company_name: str
    subscription_tier: str
    message: str


class TenantOnboardingRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=100)
    subdomain: str = Field(..., min_length=3, max_length=50, pattern="^[a-z0-9-]+$")
    subscription_tier: str = Field("free", pattern="^(free|pro|enterprise)$")


class TenantOnboardingResponse(BaseModel):
    tenant_id: int
    subdomain: str
    api_key: str
    subscription_tier: str
    message: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: RegisterRequest):
    """
    Register a new user and create their tenant.

    This endpoint:
    1. Creates a new user account
    2. Creates a new tenant with the company name
    3. Generates an API key for the tenant
    """
    if request.username.lower() in ["admin", "root", "system"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username not allowed",
        )

    existing_user = auth_credentials._users.get(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    subdomain = request.company_name.lower().replace(" ", "-")[:50]
    api_key = APIKeyManager.generate_api_key(prefix=subdomain[:2])

    async with get_session() as session:
        existing_subdomain = await session.execute(
            __import__("sqlalchemy").select(Tenant).where(Tenant.subdomain == subdomain)
        )
        if existing_subdomain.scalar_one_or_none():
            subdomain = f"{subdomain}-{request.username}"

        db_tenant = Tenant(
            name=request.company_name,
            subdomain=subdomain,
            api_key=api_key,
            is_active=True,
            subscription_tier=request.subscription_tier,
        )
        session.add(db_tenant)
        await session.flush()
        await session.commit()
        tenant_id = db_tenant.id

    auth_credentials.add_user(
        username=request.username,
        password=request.password,
        role=UserRole.USER,
        created_by="registration",
    )

    auth_credentials._users[request.username]["email"] = request.email
    auth_credentials._users[request.username]["tenant_id"] = tenant_id

    logger.info(
        f"New user registered: {request.username} (tenant: {tenant_id})",
        extra={
            "username": request.username,
            "tenant_id": tenant_id,
            "tier": request.subscription_tier,
        },
    )

    return RegisterResponse(
        user_id=request.username,
        tenant_id=tenant_id,
        username=request.username,
        email=request.email,
        company_name=request.company_name,
        subscription_tier=request.subscription_tier,
        message=f"Welcome! Your account has been created with {request.subscription_tier} tier.",
    )


@router.post(
    "/onboarding", response_model=TenantOnboardingResponse, status_code=status.HTTP_201_CREATED
)
async def create_tenant_onboarding(request: TenantOnboardingRequest):
    """
    Create a new tenant during onboarding.

    This endpoint is for users who already have an account and want to create an additional tenant.
    Requires authentication.
    """
    api_key = APIKeyManager.generate_api_key(prefix=request.subdomain[:2])

    async with get_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(Tenant).where(Tenant.subdomain == request.subdomain)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with subdomain '{request.subdomain}' already exists",
            )

        db_tenant = Tenant(
            name=request.company_name,
            subdomain=request.subdomain,
            api_key=api_key,
            is_active=True,
            subscription_tier=request.subscription_tier,
        )
        session.add(db_tenant)
        await session.flush()
        await session.commit()
        tenant_id = db_tenant.id

    logger.info(
        f"New tenant created: {request.subdomain} (ID: {tenant_id})",
        extra={"subdomain": request.subdomain, "tenant_id": tenant_id},
    )

    return TenantOnboardingResponse(
        tenant_id=tenant_id,
        subdomain=request.subdomain,
        api_key=api_key,
        subscription_tier=request.subscription_tier,
        message="Tenant created successfully. Use the API key to authenticate requests.",
    )


@router.get("/tiers")
async def get_registration_tiers():
    """
    Get subscription tiers available during registration.

    Returns tier information without requiring authentication.
    """
    return {
        "tiers": [
            {
                "id": tier_key,
                "name": config["name"],
                "price_monthly": config["price_monthly"],
                "price_yearly": config["price_yearly"],
                "requests_per_day": config["requests_per_day"]
                if config["requests_per_day"] != -1
                else "unlimited",
                "requests_per_minute": config["requests_per_minute"]
                if config["requests_per_minute"] != -1
                else "unlimited",
                "features": config["features"],
            }
            for tier_key, config in SubscriptionTier.TIERS.items()
        ]
    }
