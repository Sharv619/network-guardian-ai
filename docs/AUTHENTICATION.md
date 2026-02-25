# Authentication Guide

## Overview

Network Guardian AI now includes a comprehensive authentication and authorization system with:

- **API Key Authentication** - For service-to-service communication
- **JWT Token Authentication** - For user sessions
- **Role-Based Access Control (RBAC)** - Admin, User, Viewer roles
- **Security Headers** - HSTS, CSP, X-Frame-Options, etc.

## Quick Start

### Default Credentials

**IMPORTANT: Change these in production!**

- **Username**: `admin`
- **Password**: `admin123`
- **Default API Key**: `ng_default_admin_key_change_in_production`

### Authentication Methods

#### 1. JWT Token Authentication

**Login to get tokens:**

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Use the token:**

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ0eXAi..."
```

#### 2. API Key Authentication

**Using API Key header:**

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "X-API-Key: ng_default_admin_key_change_in_production"
```

## User Roles & Permissions

### Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `admin` | Full system access | read, write, delete, manage_users, manage_keys |
| `user` | Standard user | read, write, delete |
| `viewer` | Read-only access | read |

### Checking Permissions

You can check your current permissions via the `/auth/me` endpoint:

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
  "identity": "admin",
  "role": "admin",
  "auth_type": "jwt",
  "permissions": ["read", "write", "delete", "manage_users", "manage_keys"]
}
```

## Managing API Keys

### Create API Key (Admin Only)

```bash
curl -X POST http://localhost:8000/auth/api-keys \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "monitoring_service",
    "role": "viewer"
  }'
```

**Response:**
```json
{
  "api_key": "ng_a1b2c3d4e5f6...",
  "name": "monitoring_service",
  "role": "viewer",
  "created_at": "2026-02-20T10:30:00"
}
```

### List API Keys (Admin Only)

```bash
curl -X GET http://localhost:8000/auth/api-keys \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Revoke API Key (Admin Only)

```bash
curl -X DELETE http://localhost:8000/auth/api-keys/monitoring_service \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Managing Users

### Create User (Admin Only)

```bash
curl -X POST http://localhost:8000/auth/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst",
    "password": "secure_password",
    "role": "user"
  }'
```

### List Users (Admin Only)

```bash
curl -X GET http://localhost:8000/auth/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Deactivate User (Admin Only)

```bash
curl -X DELETE http://localhost:8000/auth/users/analyst \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Token Refresh

JWT access tokens expire after 30 minutes. Use the refresh token to get a new access token:

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

## Endpoints

### Public Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/auth/token` | POST | Login and get JWT tokens | No |
| `/auth/refresh` | POST | Refresh access token | No |
| `/auth/status` | GET | Check authentication status | No |

### Authenticated Endpoints

| Endpoint | Method | Description | Auth Required | Role |
|----------|--------|-------------|---------------|------|
| `/auth/me` | GET | Get current user profile | Yes | Any |
| `/auth/api-keys` | POST | Create API key | Yes | Admin |
| `/auth/api-keys` | GET | List API keys | Yes | Admin |
| `/auth/api-keys/{name}` | DELETE | Revoke API key | Yes | Admin |
| `/auth/users` | POST | Create user | Yes | Admin |
| `/auth/users` | GET | List users | Yes | Admin |
| `/auth/users/{username}` | DELETE | Deactivate user | Yes | Admin |

## Security Features

### Security Headers

All responses include security headers:

- **Strict-Transport-Security**: Forces HTTPS (1 year, includes subdomains)
- **X-Content-Type-Options**: Prevents MIME sniffing
- **X-Frame-Options**: Prevents clickjacking (DENY)
- **X-XSS-Protection**: XSS protection enabled
- **Content-Security-Policy**: Restricts resource loading
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Restricts browser features

### Rate Limiting

- **Limit**: 100 requests per minute per IP
- **Response**: 429 Too Many Requests when exceeded

### CORS Configuration

- Configurable via `ALLOWED_ORIGINS` in `.env`
- Credentials allowed
- Specific headers allowed
- Max age: 1 hour

## Production Checklist

Before deploying to production:

1. **Change default credentials**
   - Update admin password
   - Revoke default API key
   - Create new admin API key

2. **Configure HTTPS**
   - Enable HTTPS redirection
   - Set up SSL certificates
   - Update `ALLOWED_ORIGINS`

3. **Review CORS settings**
   - Restrict to your domain
   - Remove localhost in production

4. **Implement user store**
   - Replace in-memory storage with database
   - Add password complexity requirements
   - Implement account lockout

5. **Add logging**
   - Log authentication attempts
   - Monitor failed logins
   - Track API key usage

## Examples

### Python Client

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/auth/token",
    data={"username": "admin", "password": "admin123"}
)
tokens = response.json()
access_token = tokens["access_token"]

# Make authenticated request
response = requests.get(
    "http://localhost:8000/auth/me",
    headers={"Authorization": f"Bearer {access_token}"}
)
print(response.json())

# Using API key
response = requests.get(
    "http://localhost:8000/auth/me",
    headers={"X-API-Key": "ng_default_admin_key_change_in_production"}
)
print(response.json())
```

### JavaScript Client

```javascript
// Login
const response = await fetch('http://localhost:8000/auth/token', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: 'username=admin&password=admin123'
});

const tokens = await response.json();
const accessToken = tokens.access_token;

// Make authenticated request
const userResponse = await fetch('http://localhost:8000/auth/me', {
  headers: {'Authorization': `Bearer ${accessToken}`}
});

const user = await userResponse.json();
console.log(user);
```

## Troubleshooting

### 401 Unauthorized

- Check token is included in Authorization header
- Verify token format: `Bearer <token>`
- Ensure token hasn't expired
- Try refreshing the token

### 403 Forbidden

- User doesn't have required role
- Check user permissions via `/auth/me`
- Admin operations require admin role

### 429 Too Many Requests

- Rate limit exceeded
- Wait 60 seconds before retrying
- Consider implementing exponential backoff

## Implementation Details

### Dependencies

- **PyJWT**: JWT token generation and validation
- **passlib**: Password hashing with bcrypt
- **python-multipart**: Form data parsing for login

### Token Structure

JWT tokens contain:
- `sub`: Subject (username)
- `role`: User role
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp
- `type`: Token type (access_token or refresh_token)

### Storage

**Current implementation uses in-memory storage:**

- API keys stored in `AuthCredentials._api_keys`
- Users stored in `AuthCredentials._users`

**Production implementation should use:**
- Database-backed user store (PostgreSQL, MySQL)
- Encrypted credential storage
- Session management
- Audit logging
