"""
Tests for authentication and authorization system.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app
from backend.core.auth import (
    APIKeyManager,
    PasswordManager,
    JWTManager,
    UserRole,
    auth_credentials,
)


client = TestClient(app)


class TestAPIKeyManager:
    """Test API key generation and validation."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = APIKeyManager.generate_api_key()
        
        assert api_key.startswith("ng_")
        assert len(api_key) == 35
    
    def test_hash_and_verify_api_key(self):
        """Test API key hashing and verification."""
        api_key = "ng_test1234567890"
        hashed = APIKeyManager.hash_api_key(api_key)
        
        assert hashed != api_key
        assert len(hashed) == 64
        assert APIKeyManager.verify_api_key(api_key, hashed) is True
        assert APIKeyManager.verify_api_key("wrong_key", hashed) is False
    
    def test_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        key1 = APIKeyManager.generate_api_key()
        key2 = APIKeyManager.generate_api_key()
        
        assert key1 != key2


class TestPasswordManager:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password123"
        hashed = PasswordManager.hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")
    
    def test_verify_password(self):
        """Test password verification."""
        password = "test_password123"
        hashed = PasswordManager.hash_password(password)
        
        assert PasswordManager.verify_password(password, hashed) is True
        assert PasswordManager.verify_password("wrong_password", hashed) is False


class TestJWTManager:
    """Test JWT token creation and validation."""
    
    def test_create_access_token(self):
        """Test JWT access token creation."""
        data = {"sub": "testuser", "role": "admin"}
        token = JWTManager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_access_token(self):
        """Test JWT token decoding."""
        data = {"sub": "testuser", "role": "admin"}
        token = JWTManager.create_access_token(data)
        
        decoded = JWTManager.decode_access_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"
        assert decoded["type"] == "access_token"
    
    def test_decode_invalid_token(self):
        """Test decoding invalid JWT token."""
        invalid_token = "invalid.token.here"
        
        decoded = JWTManager.decode_access_token(invalid_token)
        
        assert decoded is None
    
    def test_create_refresh_token(self):
        """Test JWT refresh token creation."""
        data = {"sub": "testuser", "role": "admin"}
        token = JWTManager.create_refresh_token(data)
        
        decoded = JWTManager.decode_access_token(token)
        
        assert decoded is not None
        assert decoded["type"] == "refresh_token"


class TestUserRole:
    """Test user role permissions."""
    
    def test_admin_permissions(self):
        """Test admin role has all permissions."""
        admin_perms = UserRole.PERMISSIONS[UserRole.ADMIN]
        
        assert "read" in admin_perms
        assert "write" in admin_perms
        assert "delete" in admin_perms
        assert "manage_users" in admin_perms
        assert "manage_keys" in admin_perms
    
    def test_user_permissions(self):
        """Test user role has limited permissions."""
        user_perms = UserRole.PERMISSIONS[UserRole.USER]
        
        assert "read" in user_perms
        assert "write" in user_perms
        assert "delete" in user_perms
        assert "manage_users" not in user_perms
        assert "manage_keys" not in user_perms
    
    def test_viewer_permissions(self):
        """Test viewer role has read-only permissions."""
        viewer_perms = UserRole.PERMISSIONS[UserRole.VIEWER]
        
        assert "read" in viewer_perms
        assert "write" not in viewer_perms
        assert "delete" not in viewer_perms


class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_login_endpoint_success(self):
        """Test successful login."""
        response = client.post(
            "/auth/token",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_endpoint_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = client.post(
            "/auth/token",
            json={
                "username": "admin",
                "password": "wrong_password"
            }
        )
        
        assert response.status_code == 401
    
    def test_auth_status_unauthenticated(self):
        """Test auth status without authentication."""
        response = client.get("/auth/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is False
    
    def test_auth_status_with_token(self):
        """Test auth status with valid JWT token."""
        login_response = client.post(
            "/auth/token",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/auth/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is True
        assert data["user"]["role"] == "admin"
    
    def test_me_endpoint_requires_auth(self):
        """Test /auth/me endpoint requires authentication."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_me_endpoint_with_auth(self):
        """Test /auth/me endpoint with authentication."""
        login_response = client.post(
            "/auth/token",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["identity"] == "admin"
        assert data["role"] == "admin"


class TestAPIKeyEndpoints:
    """Test API key management endpoints."""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin JWT token for authenticated requests."""
        response = client.post(
            "/auth/token",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        return response.json()["access_token"]
    
    def test_create_api_key_requires_admin(self):
        """Test API key creation requires admin role."""
        response = client.post(
            "/auth/api-keys",
            json={
                "name": "test_key",
                "role": "viewer"
            }
        )
        
        assert response.status_code == 401
    
    def test_create_api_key_with_admin(self, admin_token):
        """Test API key creation with admin authentication."""
        response = client.post(
            "/auth/api-keys",
            json={
                "name": "test_key",
                "role": "viewer"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["name"] == "test_key"
        assert data["role"] == "viewer"
    
    def test_list_api_keys_requires_admin(self):
        """Test listing API keys requires admin role."""
        response = client.get("/auth/api-keys")
        
        assert response.status_code == 401
    
    def test_list_api_keys_with_admin(self, admin_token):
        """Test listing API keys with admin authentication."""
        response = client.get(
            "/auth/api-keys",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestUserEndpoints:
    """Test user management endpoints."""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin JWT token for authenticated requests."""
        response = client.post(
            "/auth/token",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        return response.json()["access_token"]
    
    def test_create_user_requires_admin(self):
        """Test user creation requires admin role."""
        response = client.post(
            "/auth/users",
            json={
                "username": "newuser",
                "password": "password123",
                "role": "viewer"
            }
        )
        
        assert response.status_code == 401
    
    def test_list_users_requires_admin(self):
        """Test listing users requires admin role."""
        response = client.get("/auth/users")
        
        assert response.status_code == 401
    
    def test_list_users_with_admin(self, admin_token):
        """Test listing users with admin authentication."""
        response = client.get(
            "/auth/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
