"""
Pydantic models for authentication and authorization.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TokenData(BaseModel):
    """Data extracted from a decoded JWT token."""
    sub: str = Field(..., description="Subject (username)")
    role: str = Field(..., description="User role")


class Token(BaseModel):
    """JWT token response (simplified)."""
    access_token: str
    token_type: str = "bearer"


class UserCredentials(BaseModel):
    """User login credentials."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    """User login request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class APIKeyCreate(BaseModel):
    """Create new API key request."""
    name: str = Field(..., min_length=3, max_length=50)
    role: str = Field(..., description="Role: admin, user, or viewer")


class APIKeyResponse(BaseModel):
    """API key response."""
    api_key: str
    name: str
    role: str
    created_at: str


class APIKeyListResponse(BaseModel):
    """API key list item."""
    name: str
    role: str
    created_at: str
    is_active: bool


class UserCreate(BaseModel):
    """Create new user request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field(..., description="Role: admin, user, or viewer")


class UserResponse(BaseModel):
    """User response."""
    username: str
    role: str
    created_at: str
    is_active: bool


class UserProfile(BaseModel):
    """User profile information."""
    identity: str
    role: str
    auth_type: str
    permissions: list[str]


class AuthStatus(BaseModel):
    """Authentication status response."""
    is_authenticated: bool
    user: Optional[UserProfile] = None
