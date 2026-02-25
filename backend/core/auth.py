"""
Authentication and Authorization Module for Network Guardian AI.

This module provides:
- API Key authentication
- JWT token authentication
- Role-based access control (RBAC)
- Password hashing utilities
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from passlib.context import CryptContext

from backend.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthConfig:
    """Authentication configuration."""
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_KEY_HEADER: str = "X-API-Key"
    AUTHORIZATION_HEADER: str = "Authorization"
    
    @property
    def SECRET_KEY(self) -> str:
        """Get JWT secret key from settings."""
        return settings.JWT_SECRET_KEY


class UserRole:
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    
    ALL_ROLES = [ADMIN, USER, VIEWER]
    
    PERMISSIONS = {
        ADMIN: ["read", "write", "delete", "manage_users", "manage_keys"],
        USER: ["read", "write", "delete"],
        VIEWER: ["read"],
    }


class APIKeyManager:
    """Manage API keys for authentication."""
    
    @staticmethod
    def generate_api_key(prefix: str = "ng") -> str:
        """Generate a secure API key."""
        random_bytes = secrets.token_bytes(32)
        key_hash = hashlib.sha256(random_bytes).hexdigest()
        return f"{prefix}_{key_hash[:32]}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash."""
        return secrets.compare_digest(
            APIKeyManager.hash_api_key(api_key),
            hashed_key
        )


class PasswordManager:
    """Manage password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)


class JWTManager:
    """Manage JWT tokens."""
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access_token"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            AuthConfig().SECRET_KEY,
            algorithm=AuthConfig.ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT access token."""
        try:
            payload = jwt.decode(
                token,
                AuthConfig().SECRET_KEY,
                algorithms=[AuthConfig.ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token (longer expiry)."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh_token"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            AuthConfig().SECRET_KEY,
            algorithm=AuthConfig.ALGORITHM
        )
        
        return encoded_jwt


class AuthCredentials:
    """Valid authentication credentials storage.
    
    In production, this should be replaced with a database-backed user store.
    For now, we'll use environment variables or a config file.
    """
    
    _instance = None
    _api_keys: Dict[str, Dict[str, Any]] = {}
    _users: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_defaults()
        return cls._instance
    
    def _initialize_defaults(self) -> None:
        """Initialize default admin credentials."""
        default_api_key = "ng_default_admin_key_change_in_production"
        hashed_key = APIKeyManager.hash_api_key(default_api_key)
        
        self._api_keys = {
            hashed_key: {
                "key_hash": hashed_key,
                "role": UserRole.ADMIN,
                "name": "default_admin",
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True,
            }
        }
        
        default_password = "admin123"
        hashed_password = PasswordManager.hash_password(default_password)
        
        self._users = {
            "admin": {
                "username": "admin",
                "hashed_password": hashed_password,
                "role": UserRole.ADMIN,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
            }
        }
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return its metadata."""
        hashed_key = APIKeyManager.hash_api_key(api_key)
        key_data = self._api_keys.get(hashed_key)
        
        if key_data and key_data.get("is_active", False):
            return key_data
        
        return None
    
    def validate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Validate user credentials."""
        user = self._users.get(username)
        
        if not user:
            return None
        
        if not user.get("is_active", False):
            return None
        
        if not PasswordManager.verify_password(password, user["hashed_password"]):
            return None
        
        return user
    
    def add_api_key(
        self,
        api_key: str,
        role: str,
        name: str,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """Add a new API key."""
        hashed_key = APIKeyManager.hash_api_key(api_key)
        
        key_data = {
            "key_hash": hashed_key,
            "role": role,
            "name": name,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
        }
        
        self._api_keys[hashed_key] = key_data
        return key_data
    
    def add_user(
        self,
        username: str,
        password: str,
        role: str,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """Add a new user."""
        hashed_password = PasswordManager.hash_password(password)
        
        user_data = {
            "username": username,
            "hashed_password": hashed_password,
            "role": role,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
        }
        
        self._users[username] = user_data
        return user_data
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        hashed_key = APIKeyManager.hash_api_key(api_key)
        
        if hashed_key in self._api_keys:
            self._api_keys[hashed_key]["is_active"] = False
            return True
        
        return False
    
    def deactivate_user(self, username: str) -> bool:
        """Deactivate a user account."""
        if username in self._users:
            self._users[username]["is_active"] = False
            return True
        
        return False
    
    def list_api_keys(self) -> list:
        """List all API keys (without revealing the actual keys)."""
        return [
            {
                "name": data["name"],
                "role": data["role"],
                "created_at": data["created_at"],
                "is_active": data["is_active"],
            }
            for data in self._api_keys.values()
        ]
    
    def list_users(self) -> list:
        """List all users (without passwords)."""
        return [
            {
                "username": data["username"],
                "role": data["role"],
                "created_at": data["created_at"],
                "is_active": data["is_active"],
            }
            for data in self._users.values()
        ]


auth_credentials = AuthCredentials()
