# AGENTS.md - Network Guardian AI

FastAPI-based network security tool that intercepts DNS via AdGuard, analyzes domains with Gemini AI and ML heuristics (Shannon Entropy, Isolation Forest), and logs to Google Sheets. Now being converted to a multi-tenant Security-as-a-Service platform.

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
# Production/All-in-one: Backend serves frontend from port 8000
PYTHONPATH=. python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Development: Run backend + separate frontend dev server
# Backend on 8000, Frontend on 3000 (proxies to backend)
PYTHONPATH=. python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
cd frontend && npm run dev

# Build frontend for production (copies to backend/static)
cd frontend && npm run build
# Then copy: cp -r frontend/dist/* backend/static/

# MCP Server (for tool access)
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
# Test specific tenant functionality
PYTHONPATH=. python -m pytest Tests_AI/ -k "tenant" -v
```

### Linting & Type Checking
```bash
ruff check backend/ && ruff check backend/ --fix  # fix auto-fixable
mypy backend/ --ignore-missing-imports
```

## Project Structure
```
backend/
├── api/          # FastAPI routes (chat.py, router.py, stats.py, tenant_router.py, etc.)
├── core/         # Config, state, auth, websocket manager, tenant_middleware
├── db/           # SQLAlchemy models, repository, database (with multi-tenancy support)
├── logic/        # ML heuristics, anomaly detection, vector store
├── services/     # External integrations (AdGuard, Gemini, Sheets)
Tests_AI/         # pytest unit/integration tests
frontend/
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
- Line length: 100 chars max, 4 spaces, no tabs
- Python 3.10+ type hints required on all functions
- Union syntax preferred: `dict[str, Any] | None` (avoid `Optional[X]` for new code)
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
- Async functions must be called with `await` or `asyncio.run()`
- Calling async from sync context returns a coroutine (TypeError on dict access)
- Use proper async session handling: `async with get_session() as session:`

### API Design
- Return JSON, use Pydantic models for validation
- HTTP status codes: 200, 401, 422, 429, 500
- Docstrings on all endpoints
- Include tenant_id in API responses where relevant
- Use proper error responses with detail messages

### Database & State
- In-memory for session state (lists, dicts)
- SQLite via SQLAlchemy for persistence with tenant_id columns
- Repository pattern for DB operations with tenant scoping
- All database queries must include tenant filtering
- Use async database sessions throughout

### Testing
- Tests in `Tests_AI/`, use `pytest`
- Mock external services (Gemini, AdGuard, Sheets)
- Include both unit tests and integration tests
- Test tenant isolation and data separation
- Test API key validation and permissions

### Security
- Never log API keys/credentials
- Validate inputs with `is_valid_domain()` before processing
- Keep secrets in `.env`, never commit them
- Implement proper tenant isolation to prevent data leakage
- Use API keys for tenant authentication in addition to JWT
- Rate limit per tenant/API key

## Key Features
1. **Real-time DNS Analysis**: AdGuard interception, Shannon Entropy, Isolation Forest, Gemini AI
2. **Vector Store & RAG**: SQLAlchemy persistence, hybrid search, semantic context
3. **Conversational Chatbot**: Short responses (<=3 words), full domain analysis, real-time stats
4. **WebSocket**: `/ws`, `/ws/public`, `/ws/admin` for real-time updates
5. **Multi-tenancy**: Complete tenant isolation with separate data, configurations, and API keys
6. **Tenant Management**: API for tenant creation, configuration, and management
7. **Security-as-a-Service**: Ready for commercial offering with billing integration

## Environment Variables
```bash
GEMINI_API_KEY, NOTION_TOKEN, GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEET_ID
ADGUARD_URL, ADGUARD_USER, ADGUARD_PASS
OLLAMA_ENABLED, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_CHAT_MODEL
EMBEDDING_PROVIDER=sentence-transformers  # or "ollama", "mock"
# New for multi-tenancy:
API_RATE_LIMIT_PER_TENANT=100  # Requests per minute per tenant
DEFAULT_TENANT_ID=1  # Default tenant for backward compatibility
```

## Known Issues
- Isolation Forest needs 10+ samples before detecting anomalies
- sentence-transformers not installed by default
- Gemini API rate limits → falls back to heuristics
- Tenant management API requires admin authentication (to be integrated with auth system)
- WebSocket tenant broadcasting needs further testing
- Frontend updates needed for tenant awareness (Phase 5)

## Current Progress

✅ Phase 1 Foundation - Multi-tenancy & Customer Isolation:
- Database schema updated with tenant_id columns
- Tenant table created with proper indexing
- Repository layer updated for tenant scoping
- Tenant middleware implemented for request-based tenant identification
- WebSocket manager updated for tenant-aware connections
- Core API endpoints updated to be tenant-aware
- Tenant management API created (tenant_router.py)
- System intelligence display updated to work with tenant context

✅ Phase 2 - Customer Management & Billing:
- User registration API with tenant creation (registration_router.py)
- Stripe billing integration (billing_service.py, billing_router.py)
- Subscription management (create checkout, portal, cancel)
- Usage tracking per tenant (daily and overall stats)
- Subscription webhooks for automated tier updates
- Documentation updated with complete API reference

✅ Phase 3 - Public API & Developer Experience:
- Developer portal API (developer_router.py)
- API key generation and management per tenant
- Tier-based rate limiting (tier_rate_limiter.py)
- Usage analytics per API key
- Rate limit headers in responses
- Public API documentation endpoint

✅ Phase 5 - Customer Experience:
- Login/Registration UI (LoginPage.tsx)
- Admin Dashboard for tenant management (AdminDashboard.tsx)
- Tenant Selector dropdown (TenantSelector.tsx)
- Pricing/Subscription page (PricingPage.tsx)
- Usage Dashboard with charts (UsageDashboard.tsx)
- API service layer (tenantService.ts)

🔜 Phase 4 - Operational Excellence:
- Kubernetes manifests for deployment
- Monitoring and alerting setup
- Backup and recovery procedures

🔜 Phase 6 - Advanced Features:
- Compliance reporting
- Advanced analytics
- SIEM integrations

## Next Steps
1. Deploy infrastructure (Phase 4)
2. Add compliance features (Phase 6)

## New Environment Variables
```bash
# Stripe Billing
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...
```