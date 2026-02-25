"""
Authentication and Authorization API routes.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from backend.api.models_auth import (
    LoginRequest,
    TokenResponse,
    Token,
    UserCredentials,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    UserCreate,
    UserResponse,
    UserProfile,
    AuthStatus,
)
from backend.core.auth import (
    auth_credentials,
    JWTManager,
    APIKeyManager,
    UserRole,
    AuthConfig,
)
from backend.core.deps import (
    AuthenticatedUser,
    require_authentication,
    require_admin,
    get_current_user,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/token", response_model=Token)
async def login(credentials: UserCredentials):
    """
    Login with username and password to get a JWT token.
    
    Accepts UserCredentials and returns a simplified Token response.
    """
    user = auth_credentials.validate_user(
        credentials.username,
        credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "sub": user["username"],
        "role": user["role"]
    }
    
    access_token = JWTManager.create_access_token(token_data)
    
    return Token(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login_full(login_request: LoginRequest):
    """
    Login with username and password to get JWT tokens (full response).
    
    Returns access_token, refresh_token, and expiry information.
    """
    user = auth_credentials.validate_user(
        login_request.username,
        login_request.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "sub": user["username"],
        "role": user["role"]
    }
    
    access_token = JWTManager.create_access_token(token_data)
    refresh_token = JWTManager.create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.
    """
    payload = JWTManager.decode_access_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "sub": payload["sub"],
        "role": payload["role"]
    }
    
    new_access_token = JWTManager.create_access_token(token_data)
    new_refresh_token = JWTManager.create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/status", response_model=AuthStatus)
async def get_auth_status(
    current_user: AuthenticatedUser | None = Depends(get_current_user)
):
    """
    Get current authentication status.
    
    Returns user information if authenticated.
    """
    if current_user:
        return AuthStatus(
            is_authenticated=True,
            user=UserProfile(
                identity=current_user.identity,
                role=current_user.role,
                auth_type=current_user.auth_type,
                permissions=current_user.permissions
            )
        )
    
    return AuthStatus(is_authenticated=False)


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(require_authentication)
):
    """
    Get current user profile.
    
    Requires authentication.
    """
    return UserProfile(
        identity=current_user.identity,
        role=current_user.role,
        auth_type=current_user.auth_type,
        permissions=current_user.permissions
    )


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_request: APIKeyCreate,
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Create a new API key.
    
    Requires admin role.
    """
    if api_key_request.role not in UserRole.ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {UserRole.ALL_ROLES}"
        )
    
    api_key = APIKeyManager.generate_api_key()
    
    key_data = auth_credentials.add_api_key(
        api_key=api_key,
        role=api_key_request.role,
        name=api_key_request.name,
        created_by=current_user.identity
    )
    
    return APIKeyResponse(
        api_key=api_key,
        name=key_data["name"],
        role=key_data["role"],
        created_at=key_data["created_at"]
    )


@router.get("/api-keys", response_model=list[APIKeyListResponse])
async def list_api_keys(
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    List all API keys.
    
    Requires admin role.
    """
    keys = auth_credentials.list_api_keys()
    
    return [
        APIKeyListResponse(
            name=key["name"],
            role=key["role"],
            created_at=key["created_at"],
            is_active=key["is_active"]
        )
        for key in keys
    ]


@router.delete("/api-keys/{key_name}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_name: str,
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Revoke an API key by name.
    
    Requires admin role.
    """
    keys = auth_credentials.list_api_keys()
    key_to_revoke = None
    
    for key in keys:
        if key["name"] == key_name:
            key_to_revoke = key
            break
    
    if not key_to_revoke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return None


@router.get("/keys", response_model=list[APIKeyListResponse])
async def list_keys(
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    List all API keys (alias for /auth/api-keys).
    
    Requires admin role.
    """
    keys = auth_credentials.list_api_keys()
    
    return [
        APIKeyListResponse(
            name=key["name"],
            role=key["role"],
            created_at=key["created_at"],
            is_active=key["is_active"]
        )
        for key in keys
    ]


class GenerateKeyRequest(BaseModel):
    """Request body for generating a new API key."""
    name: str = Field(..., min_length=3, max_length=50)
    role: str = Field(..., description="Role: admin, user, or viewer")


@router.post("/generate-key", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_key(
    key_request: GenerateKeyRequest,
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Generate a new API key.
    
    **SENSITIVE:** Returns the plaintext API key. This is the only time
    the key will be shown - copy it immediately!
    
    Requires admin role.
    """
    if key_request.role not in UserRole.ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {UserRole.ALL_ROLES}"
        )
    
    api_key = APIKeyManager.generate_api_key()
    
    key_data = auth_credentials.add_api_key(
        api_key=api_key,
        role=key_request.role,
        name=key_request.name,
        created_by=current_user.identity
    )
    
    return APIKeyResponse(
        api_key=api_key,
        name=key_data["name"],
        role=key_data["role"],
        created_at=key_data["created_at"]
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_request: UserCreate,
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Create a new user.
    
    Requires admin role.
    """
    if user_request.role not in UserRole.ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {UserRole.ALL_ROLES}"
        )
    
    user_data = auth_credentials.add_user(
        username=user_request.username,
        password=user_request.password,
        role=user_request.role,
        created_by=current_user.identity
    )
    
    return UserResponse(
        username=user_data["username"],
        role=user_data["role"],
        created_at=user_data["created_at"],
        is_active=user_data["is_active"]
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    List all users.
    
    Requires admin role.
    """
    users = auth_credentials.list_users()
    
    return [
        UserResponse(
            username=user["username"],
            role=user["role"],
            created_at=user["created_at"],
            is_active=user["is_active"]
        )
        for user in users
    ]


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    username: str,
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Deactivate a user account.
    
    Requires admin role.
    """
    if not auth_credentials.deactivate_user(username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return None
