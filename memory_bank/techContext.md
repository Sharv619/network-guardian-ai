# Network Guardian AI: Technical Context

## Tech Stack

### AI/ML Components
- **Google Gemini 1.5 Flash**: Primary AI model for threat analysis and explanation generation
- **Scikit-Learn (Isolation Forest)**: Unsupervised learning model for behavioral anomaly detection
- **Shannon Entropy**: Mathematical heuristic for detecting DGA (Domain Generation Algorithm) patterns

### Backend Technologies
- **Python 3.12**: Core runtime environment
- **FastAPI**: High-performance web framework for API development
- **Uvicorn**: ASGI server for running FastAPI applications

### Frontend Technologies
- **React**: Component-based UI framework
- **TypeScript**: Type-safe JavaScript superset
- **Tailwind CSS**: Utility-first CSS framework
- **Vite**: Build tool and development server

### Data Persistence
- **Google Sheets API**: Primary data lake for security audit trails
- **Google Cloud Service Account**: Authentication for Google API access

### Infrastructure
- **Docker Compose**: Container orchestration for development and production
- **Linux Bridge Networking**: Network configuration for container communication
- **AdGuard Home**: DNS-level blocking and network monitoring

## APIs and Services

### External APIs
- **Google Gemini API**: AI-powered threat analysis and explanation
- **Google Sheets API**: Data persistence and audit trail logging
- **AdGuard Home API**: Network traffic monitoring and DNS blocking data

### Internal Services
- **AdGuard Poller**: Background service for fetching blocked domains
- **Gemini Analyzer**: AI analysis with circuit breaker pattern
- **Sheets Logger**: Google Sheets integration for data persistence
- **Notion Service**: (Legacy) Alternative data persistence option

## MCP Servers
This project does not currently utilize MCP (Model Context Protocol) servers.

## Architecture Patterns

### Backend-for-Frontend (BFF) Pattern
- AI API keys are hidden in the backend
- Browser never directly accesses sensitive credentials
- Centralized security and authentication

### Circuit Breaker Pattern
- Graceful degradation when Gemini API is throttled (429 errors)
- Automatic fallback to local heuristic analysis
- Maintains network protection during API outages

### Production-First Mindset
- Integrated heartbeat status indicators
- Standardized ISO-8601 time-series logging
- Automated Pytest suite for reliability
- Containerized deployment with Docker Compose