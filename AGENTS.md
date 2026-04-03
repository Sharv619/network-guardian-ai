# AGENTS.md - Network Guardian AI

FastAPI-based network security tool that intercepts DNS via AdGuard, analyzes domains with Gemini AI and ML heuristics (Shannon Entropy, Isolation Forest), and logs to Google Sheets. Multi-tenant Security-as-a-Service platform.

## Build & Run Commands

### Install Dependencies
```bash
# Backend
cd backend && pip install -r requirements.txt
# Frontend
cd frontend && npm install
# Optional
pip install sentence-transformers
```

### Run Servers
```bash
# Production: Backend serves frontend from port 8000
PYTHONPATH=. python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Development: Backend on 8000, Frontend on 3000 (proxies to backend)
PYTHONPATH=. python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
cd frontend && npm run dev

# Build frontend for production
cd frontend && npm run build && cp -r frontend/dist/* backend/static/

# MCP Server
python network_guardian_mcp.py
```

### Testing
```bash
# All tests
PYTHONPATH=. python -m pytest Tests_AI/ -v
# Single test
PYTHONPATH=. python -m pytest Tests_AI/test_heuristics.py::test_entropy_logic -v
# With coverage
PYTHONPATH=. pytest Tests_AI/ -v --cov=backend --cov-report=term-missing
# Specific tenant tests
PYTHONPATH=. python -m pytest Tests_AI/ -k "tenant" -v
```

### Linting & Type Checking
```bash
ruff check backend/ && ruff check backend/ --fix
mypy backend/ --ignore-missing-imports
```

## Project Structure
```
backend/
├── api/          # FastAPI routes (chat.py, router.py, stats.py, tenant_router.py, etc.)
├── core/         # Config, state, auth, websocket manager, tenant_middleware
├── db/           # SQLAlchemy models, repository, database (multi-tenancy)
├── logic/        # ML heuristics, anomaly detection, vector store, RAG
├── services/     # External integrations (AdGuard, Gemini, Sheets, Stripe)
Tests_AI/         # pytest unit/integration tests
frontend/        # React + TypeScript + Tailwind
```

## Code Style Guidelines

### Imports
- Use absolute imports: `from backend.logic.ml_heuristics import ...`
- Group order: stdlib → third-party → local, sorted alphabetically
```python
import os
from datetime import datetime, UTC

import numpy as np
from fastapi import APIRouter

from backend.core.config import settings
from backend.db.models import Tenant
```

### Formatting & Types
- Line length: 100 chars max, 4 spaces indent, no tabs
- Python 3.10+ type hints required on all functions
- Union syntax: `dict[str, Any] | None` (avoid `Optional[X]` for new code)
```python
def calculate_entropy(domain: str) -> float:
    ...
```

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `ml_heuristics.py` |
| Classes | PascalCase | `AnomalyEngine` |
| Functions/vars | snake_case | `calculate_entropy` |
| Constants | SCREAMING_SNAKE_CASE | `POLL_INTERVAL` |
| Private methods | `_prefix` | `_heuristic_fallback` |
| Tenant ID | tenant_id | `tenant_id: int` |

### Error Handling
- Use specific exception types, log before re-raising
- Never expose raw exceptions to API responses
- Implement graceful degradation with sensible defaults
```python
try:
    analysis = analyze_domain(domain)
except SpecificException as e:
    logger.error(f"Analysis Failed: {e}", exc_info=True)
    return _fallback_result(domain)
```

### Async/Await
- Async functions must be called with `await`
- Use proper async session: `async with get_session() as session:`

### API Design
- Return JSON, use Pydantic models for validation
- HTTP status codes: 200, 401, 422, 429, 500
- Docstrings on all endpoints
- Include tenant_id in API responses where relevant

### Database & State
- In-memory for session state (lists, dicts)
- SQLite/PostgreSQL via SQLAlchemy with tenant_id columns
- Repository pattern with tenant scoping
- All DB queries must include tenant filtering

### Testing
- Tests in `Tests_AI/`, use `pytest`
- Mock external services (Gemini, AdGuard, Sheets)
- Test tenant isolation and data separation
- Test API key validation and permissions

### Security
- Never log API keys/credentials
- Validate inputs with `is_valid_domain()` before processing
- Keep secrets in `.env`, never commit them
- Implement proper tenant isolation to prevent data leakage

## Key Features
- **Real-time DNS Analysis**: AdGuard interception, Shannon Entropy, Isolation Forest, Gemini AI
- **Vector Store & RAG**: SQLAlchemy persistence, hybrid search, semantic context
- **Conversational Chatbot**: Domain analysis, real-time stats
- **WebSocket**: `/ws`, `/ws/public`, `/ws/admin` for real-time updates
- **Multi-tenancy**: Complete tenant isolation with separate data and API keys
- **Billing**: Stripe integration for subscription management

## Environment Variables
```bash
# Core
GEMINI_API_KEY, NOTION_TOKEN, GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEET_ID
ADGUARD_URL, ADGUARD_USER, ADGUARD_PASS
JWT_SECRET_KEY

# Optional ML
OLLAMA_ENABLED, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_CHAT_MODEL
EMBEDDING_PROVIDER=sentence-transformers  # or "ollama", "mock"

# Multi-tenancy
API_RATE_LIMIT_PER_TENANT=100
DEFAULT_TENANT_ID=1

# Stripe Billing
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...
```

## Known Issues
- Isolation Forest needs 10+ samples before detecting anomalies
- Gemini API rate limits → falls back to heuristics
- sentence-transformers not installed by default
- Frontend tenant awareness improvements ongoing

## Development History

### Phase 1: Foundation - Multi-tenancy & Customer Isolation
- Database schema updated with tenant_id columns
- Tenant table created with proper indexing
- Repository layer updated for tenant scoping
- Tenant middleware implemented for request-based identification
- WebSocket manager updated for tenant-aware connections
- Tenant management API created (tenant_router.py)

### Phase 2: Customer Management & Billing
- User registration API with tenant creation (registration_router.py)
- Stripe billing integration (billing_service.py, billing_router.py)
- Subscription management (create checkout, portal, cancel)
- Usage tracking per tenant (daily and overall stats)
- Subscription webhooks for automated tier updates

### Phase 3: Public API & Developer Experience
- Developer portal API (developer_router.py)
- API key generation and management per tenant
- Tier-based rate limiting (tier_rate_limiter.py)
- Usage analytics per API key
- Rate limit headers in responses

### Phase 4: Operational Excellence (In Progress)
- Kubernetes manifests for deployment
- Monitoring and alerting setup
- Backup and recovery procedures

### Phase 5: Customer Experience
- Login/Registration UI (LoginPage.tsx)
- Admin Dashboard for tenant management (AdminDashboard.tsx)
- Tenant Selector dropdown (TenantSelector.tsx)
- Pricing/Subscription page (PricingPage.tsx)
- Usage Dashboard with charts (UsageDashboard.tsx)

### Phase 6: Advanced Features (Future)
- Compliance reporting
- Advanced analytics
- SIEM integrations

## Audit Reports

### Security Audit (2024-12-15)
- **Authentication**: JWT implementation reviewed, secrets stored in environment variables
- **Tenant Isolation**: Verified tenant_id filtering in all repository queries
- **API Key Management**: Keys properly hashed, only last 4 chars exposed
- **Rate Limiting**: Per-tenant and per-API-key limiting implemented
- **Recommendations**: 
  1. Add IP-based rate limiting for login endpoints
  2. Implement MFA for admin accounts
  3. Add audit logging for tenant modifications

### Code Quality Audit (2024-12-20)
- **Type Coverage**: ~75% of functions have type hints
- **Test Coverage**: 45% backend code coverage
- **Linting**: ruff passes with 0 errors
- **Dependencies**: All critical dependencies up to date
- **Recommendations**:
  1. Increase type hints to 90% coverage
  2. Add integration tests for billing webhook flow
  3. Document all API endpoints with OpenAPI specs

### Performance Audit (2025-01-05)
- **Database**: PostgreSQL connection pooling configured, 90th percentile query < 50ms
- **API Latency**: Average response time 120ms (p95: 450ms)
- **Cache Hit Rate**: 78% for domain analysis cache
- **WebSocket**: 500 concurrent connections supported
- **Recommendations**:
  1. Add Redis for session caching
  2. Implement database read replicas
  3. Add CDN for static assets

## Next Steps
1. Deploy infrastructure (Phase 4)
2. Increase test coverage to 80%
3. Add compliance features (Phase 6)
