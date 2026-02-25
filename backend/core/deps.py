"""
FastAPI dependencies for authentication and authorization.

This module provides:
- Dependency for API Key authentication
- Dependency for JWT authentication
- Permission checking decorators
- WebSocket authentication dependencies
"""
import uuid

from fastapi import Depends, HTTPException, Query, WebSocket, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from backend.core.auth import (
    AuthConfig,
    JWTManager,
    UserRole,
    auth_credentials,
)

api_key_header = APIKeyHeader(
    name=AuthConfig.API_KEY_HEADER,
    scheme_name="api_key",
    description="API Key for authentication",
    auto_error=False
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scheme_name="jwt",
    description="JWT token authentication",
    auto_error=False
)


class AuthenticatedUser:
    """Represents an authenticated user/API key."""

    def __init__(
        self,
        identity: str,
        role: str,
        auth_type: str = "api_key"
    ):
        self.identity = identity
        self.role = role
        self.auth_type = auth_type
        self.permissions = UserRole.PERMISSIONS.get(role, [])

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def has_any_permission(self, permissions: list) -> bool:
        """Check if user has any of the specified permissions."""
        return any(perm in self.permissions for perm in permissions)

    def has_all_permissions(self, permissions: list) -> bool:
        """Check if user has all specified permissions."""
        return all(perm in self.permissions for perm in permissions)

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN


async def get_current_user(
    api_key: str | None = Depends(api_key_header),
    token: str | None = Depends(oauth2_scheme)
) -> AuthenticatedUser | None:
    """
    Get the current authenticated user from either API key or JWT token.

    This is the main authentication dependency. It checks for:
    1. API Key in X-API-Key header
    2. JWT token in Authorization header

    Returns None if no authentication is provided.
    """
    if api_key:
        key_data = auth_credentials.validate_api_key(api_key)
        if key_data:
            return AuthenticatedUser(
                identity=key_data["name"],
                role=key_data["role"],
                auth_type="api_key"
            )

    if token:
        payload = JWTManager.decode_access_token(token)
        if payload:
            return AuthenticatedUser(
                identity=payload.get("sub", "unknown"),
                role=payload.get("role", UserRole.VIEWER),
                auth_type="jwt"
            )

    return None


async def require_authentication(
    current_user: AuthenticatedUser | None = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require authentication - raises 401 if not authenticated.

    Use this dependency for endpoints that require authentication.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={
                "WWW-Authenticate": 'Bearer, APIKey realm="Network Guardian AI"'
            },
        )

    return current_user


async def require_permission(
    permission: str,
    current_user: AuthenticatedUser = Depends(require_authentication)
) -> AuthenticatedUser:
    """
    Require a specific permission.

    Use this dependency for endpoints that require specific permissions.
    """
    if not current_user.has_permission(permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required"
        )

    return current_user


def require_permissions(*permissions: str):
    """
    Decorator to require multiple permissions (any of them).

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            user: AuthenticatedUser = Depends(require_permissions("read", "write"))
        ):
            ...
    """
    async def permission_checker(
        current_user: AuthenticatedUser = Depends(require_authentication)
    ) -> AuthenticatedUser:
        if not current_user.has_any_permission(list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of permissions {list(permissions)} required"
            )

        return current_user

    return permission_checker


async def require_admin(
    current_user: AuthenticatedUser = Depends(require_authentication)
) -> AuthenticatedUser:
    """Require admin role."""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def optional_authentication(
    current_user: AuthenticatedUser | None = Depends(get_current_user)
) -> AuthenticatedUser | None:
    """
    Optional authentication - returns user if authenticated, None otherwise.

    Use this for endpoints that work with or without authentication,
    but may provide additional features when authenticated.
    """
    return current_user


async def get_current_user_ws(
    websocket: WebSocket,
    token: str | None = Query(None, alias="token"),
    api_key: str | None = Query(None, alias="api_key"),
) -> AuthenticatedUser | None:
    """
    Get the current authenticated user from WebSocket connection parameters.

    This is the WebSocket equivalent of get_current_user(). It checks for:
    1. API Key passed as query parameter 'api_key'
    2. JWT token passed as query parameter 'token'

    Returns None if no authentication is provided.
    """
    if api_key:
        key_data = auth_credentials.validate_api_key(api_key)
        if key_data:
            return AuthenticatedUser(
                identity=key_data["name"],
                role=key_data["role"],
                auth_type="api_key"
            )

    if token:
        payload = JWTManager.decode_access_token(token)
        if payload:
            return AuthenticatedUser(
                identity=payload.get("sub", "unknown"),
                role=payload.get("role", UserRole.VIEWER),
                auth_type="jwt"
            )

    return None


async def require_authentication_ws(
    websocket: WebSocket,
    current_user: AuthenticatedUser | None = Depends(get_current_user_ws)
) -> AuthenticatedUser:
    """
    Require authentication for WebSocket connections.

    Raises HTTPException with 4003 (custom WebSocket close code) if not authenticated.
    This should be called BEFORE accepting the WebSocket connection.

    Usage in WebSocket endpoint:
        @router.websocket("/ws")
        async def websocket_endpoint(
            websocket: WebSocket,
            user: AuthenticatedUser = Depends(require_authentication_ws)
        ):
            await ws_manager.connect(websocket, user)
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required for WebSocket connection",
        )

    return current_user


async def optional_authentication_ws(
    websocket: WebSocket,
    current_user: AuthenticatedUser | None = Depends(get_current_user_ws)
) -> AuthenticatedUser | None:
    """
    Optional authentication for WebSocket connections.

    Returns user if authenticated, None otherwise.
    Useful for public WebSocket endpoints that offer enhanced features when authenticated.
    """
    return current_user


def generate_client_id(user: AuthenticatedUser) -> str:
    """Generate a unique client ID for a WebSocket connection."""
    return f"{user.identity}_{uuid.uuid4().hex[:8]}"


ROLE_HIERARCHY = {
    UserRole.ADMIN: 3,
    UserRole.USER: 2,
    UserRole.VIEWER: 1,
}


def has_role_or_higher(user_role: str, required_role: str) -> bool:
    """Check if user has the required role or higher."""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level
