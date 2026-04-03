# 🛡️ Network Guardian AI
### *Multi-Tenant Security-as-a-Service Platform*

---

## 📖 Table of Contents
1. [🔍 Overview](#-overview)
2. [🕹️ Core Features](#-core-features)
3. [🏗️ System Architecture](#-system-architecture)
4. [🧠 Intelligence Layers](#-intelligence-layers)
5. [👥 Multi-Tenancy](#-multi-tenancy)
6. [💳 Billing & Subscriptions](#-billing--subscriptions)
7. [🔑 Developer API](#-developer-api)
8. [🎨 UI Components](#-ui-components)
9. [🚀 Getting Started](#-getting-started)
10. [🧪 Testing](#-testing)

---

## 🔍 Overview
Network Guardian AI is a real-time network security platform with multi-tenant support. It intercepts DNS queries via AdGuard, performs multi-layered behavioral analysis, and provides threat intelligence through a modern dashboard UI.

**Security-as-a-Service**: Ready for commercial offering with tenant isolation, billing integration, and tier-based access control.

---

## 🕹️ Core Features
*   **Real-time Threat Detection**: Live stream of DNS requests with risk assessments
*   **Manual Domain Analysis**: On-demand analysis with Gemini AI and ML heuristics
*   **12-Panel Stats Dashboard**: Comprehensive metrics overview (Overview, ML, Alerts, Blocklist, Settings)
*   **Admin Dashboard**: CRM-style tenant management interface
*   **Usage Tracking**: Per-tenant usage analytics and rate limiting
*   **Developer Portal**: API key generation and endpoint documentation

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────────┐   │
│  │  Network Guardian   │    │    AdGuard Home         │   │
│  │  (Backend + UI)    │    │    (DNS Interceptor)    │   │
│  │   Port: 8000       │    │    Port: 8080, 53       │   │
│  └─────────────────────┘    └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- **Frontend**: React/TypeScript, served from backend static
- **Backend**: Python 3.11 / FastAPI
- **Database**: SQLite with multi-tenant support
- **DNS Interceptor**: AdGuard Home
- **AI**: Google Gemini (with local heuristic fallback)

---

## 🧠 Intelligence Layers

| Layer | Method | Purpose |
| :--- | :--- | :--- |
| **Layer 1** | Shannon Entropy | Detects random DGA strings locally |
| **Layer 2** | Isolation Forest (ML) | Unsupervised anomaly detection |
| **Layer 3** | Gemini AI | Semantic threat analysis |
| **Layer 4** | Blocklist Lookup | Known threat database |

---

## 👥 Multi-Tenancy

### Tenant Management
- **Complete Isolation**: Each tenant has separate data, API keys, and configurations
- **Tenant Middleware**: Automatic tenant identification via subdomain, headers, or API key
- **Dashboard Switching**: TenantSelector component for quick context switching

### Subscription Tiers
| Tier | Features | Rate Limit |
|------|----------|------------|
| **Free** | 100 requests/min | Basic ML heuristics |
| **Pro** | Unlimited + Gemini AI | Full analysis pipeline |
| **Enterprise** | Custom + SLA | Priority support |

---

## 💳 Billing & Subscriptions

### Stripe Integration
- **Checkout Sessions**: One-click subscription upgrade
- **Customer Portal**: Self-service billing management
- **Webhook Handling**: Automated tier updates on payment events
- **Usage Tracking**: Daily and overall stats per tenant

### API Endpoints
```
POST /billing/checkout     - Create Stripe checkout session
POST /billing/portal       - Get customer portal URL
POST /billing/webhook      - Stripe webhook handler
GET  /billing/tiers        - List subscription tiers
```

---

## 🔑 Developer API

### Authentication
- **API Keys**: Per-tenant API key generation
- **JWT Support**: Token-based authentication
- **Rate Limiting**: Tier-based request limits

### Endpoints
```
POST /api/v1/analyze       - Analyze domain
GET  /api/v1/stats         - Get tenant statistics
GET  /api/v1/history       - Get threat history
WS   /ws/public            - Real-time updates
```

### Rate Limits
| Tier | Requests/Minute |
|------|----------------|
| Free | 100 |
| Pro | 1000 |
| Enterprise | Unlimited |

---

## 🎨 UI Components

### Stats Dashboard (12 Panels)
1. Blocklist KB / Known Threats
2. Ollama Models / Local AI
3. Total Decisions / Analyzed Domains
4. Autonomy Score / Local Analysis Rate
5. Patterns Learned / ML Model
6. Active Alerts / Pending
7. Anomaly Model / Training Status
8. Sources Active / Blocklist Sources
9. Vector Embeddings / Threat Storage
10. Entropy Threshold / Dynamic
11. Activity Trend Chart
12. Category Distribution Pie Chart

### Pages
- **Dashboard**: Main threat monitoring view
- **Admin**: Tenant management, CRM interface
- **Usage**: Per-tenant usage analytics
- **Pricing**: Subscription tier information

---

## 🚀 Getting Started

### 1. Environment Setup
```bash
cp .env.example .env
# Edit .env with your API keys:
GEMINI_API_KEY=your_key
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 2. Start Services
```bash
# Build and start
docker compose up --build -d

# Or just start (if image exists)
docker compose up -d
```

### 3. Access
| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:8000 |
| **AdGuard UI** | http://localhost:8080 |
| **API Docs** | http://localhost:8000/docs |

### 4. Environment Variables
```bash
# Core
GEMINI_API_KEY=your_gemini_key
ADGUARD_URL=http://adguard:80
ADGUARD_USER=admin
ADGUARD_PASS=your_password

# Stripe Billing
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...

# Ollama (optional)
OLLAMA_ENABLED=false
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2

# Multi-Tenancy
ENVIRONMENT=development  # Set to production for production
API_RATE_LIMIT_PER_TENANT=100
DEFAULT_TENANT_ID=1
```

---

## 🧪 Testing

```bash
# All tests
PYTHONPATH=. python -m pytest Tests_AI/ -v

# Single test
PYTHONPATH=. python -m pytest Tests_AI/test_heuristics.py -v

# With coverage
PYTHONPATH=. pytest Tests_AI/ -v --cov=backend

# Linting
ruff check backend/ && ruff check backend/ --fix
mypy backend/ --ignore-missing-imports
```

---

## 📊 Project Structure
```
network-guardian-ai/
├── backend/
│   ├── api/              # FastAPI routes
│   │   ├── stats.py      # Statistics endpoints
│   │   ├── chat.py       # Chatbot
│   │   ├── billing.py    # Stripe billing
│   │   ├── tenant_router.py
│   │   └── developer_router.py
│   ├── core/
│   │   ├── config.py     # Settings
│   │   ├── tenant_middleware.py
│   │   └── websocket_manager.py
│   ├── db/
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── repository.py # Data access
│   │   └── database.py   # DB connection
│   ├── logic/
│   │   ├── ml_heuristics.py
│   │   ├── anomaly_engine.py
│   │   └── metadata_classifier.py
│   └── services/
│       ├── adguard_poller.py
│       ├── gemini_service.py
│       └── blocklist_loader.py
├── frontend/
│   ├── components/
│   │   ├── Dashboard.tsx
│   │   ├── StatsPanel.tsx  # 12-panel overview
│   │   ├── AdminDashboard.tsx
│   │   ├── LoginPage.tsx
│   │   └── TenantSelector.tsx
│   ├── services/
│   │   ├── tenantService.ts
│   │   └── websocketService.ts
│   └── App.tsx
├── docker-compose.yml      # Production
├── docker-compose.dev.yml  # Development with hot-reload
├── Dockerfile              # Multi-stage build
└── Tests_AI/              # pytest tests
```

---

## 🤝 Built With
- **AI/ML**: Google Gemini, Scikit-Learn, Shannon Entropy
- **Backend**: Python 3.11, FastAPI, SQLAlchemy
- **Frontend**: React 19, TypeScript, Tailwind CSS, Recharts
- **Database**: SQLite (development), PostgreSQL-ready
- **Billing**: Stripe
- **DNS**: AdGuard Home

---

## 📈 System Status
- ✅ Multi-tenant isolation with complete data separation
- ✅ Stripe billing integration with webhook handling
- ✅ Developer API with rate limiting
- ✅ 12-panel stats dashboard
- ✅ Admin CRM interface
- ✅ Real-time WebSocket updates
- ✅ Production Docker deployment
