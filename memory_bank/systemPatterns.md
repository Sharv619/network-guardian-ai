# Network Guardian AI: System Patterns

## Code Structure Patterns

### Flat Folder Structure
The project uses a flat folder structure within each major component:
- **backend/**: Contains all Python backend code
- **frontend/**: Contains all React/TypeScript frontend code
- **memory_bank/**: Documentation and context files

### Service-Oriented Architecture
Backend services are organized by responsibility:
- **backend/services/**: External integrations and API clients
- **backend/logic/**: Core business logic and ML models
- **backend/api/**: FastAPI route definitions and models
- **backend/core/**: Configuration and state management

### Component-Based Frontend
Frontend follows React best practices:
- **frontend/components/**: Reusable UI components
- **frontend/services/**: API integration and data fetching
- **frontend/hooks/**: Custom React hooks for state management
- **frontend/api/**: Mock API for development

## Data Flow Patterns

### Real-time Data Pipeline
1. **AdGuard Poller** fetches blocked domains from AdGuard Home API
2. **ML Heuristics** applies Shannon Entropy analysis for DGA detection
3. **Anomaly Engine** uses Isolation Forest for behavioral analysis
4. **Gemini Analyzer** provides AI-powered explanations
5. **Sheets Logger** persists results to Google Sheets
6. **Frontend** displays live updates via WebSocket or polling

### Circuit Breaker Pattern
- **Primary Path**: Gemini API → Analysis → Sheets Logging
- **Fallback Path**: Local Heuristics → Sheets Logging (when Gemini is unavailable)
- **Graceful Degradation**: System remains functional during API outages

## Configuration Patterns

### Environment-Based Configuration
- **.env file**: Runtime configuration (API keys, URLs, credentials)
- **backend/core/config.py**: Application configuration and defaults
- **Docker Compose**: Container orchestration and networking

### Development vs Production
- **Development**: Mock API, local testing, hot reload
- **Production**: Containerized deployment, environment variables, monitoring

## Testing Patterns

### Automated Testing Suite
- **backend/tests/**: Unit tests for core logic and API endpoints
- **Pytest Framework**: Test runner and assertion library
- **Test Coverage**: Mathematical logic validation and API resilience testing

### Integration Testing
- **Docker Compose**: End-to-end testing with containerized services
- **Mock Services**: Simulated external APIs for reliable testing

## Deployment Patterns

### Containerized Architecture
- **Docker Compose**: Multi-service orchestration
- **Dockerfile**: Container definitions for backend and frontend
- **Linux Bridge Networking**: Container-to-container communication

### Production-First Configuration
- **Health Checks**: Container monitoring and restart policies
- **Volume Mounting**: Persistent data storage
- **Environment Variables**: Secure credential management