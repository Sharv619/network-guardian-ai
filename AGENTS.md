# AGENTS.md - Network Guardian AI

## Overview
This is a FastAPI-based network security tool that intercepts DNS requests via AdGuard, analyzes domains using Gemini AI and local ML heuristics (Shannon Entropy, Isolation Forest), and logs results to Google Sheets.

## Build & Run Commands

### Install Dependencies
```bash
cd /home/lade/Hackathons/network-guardian-ai/backend
pip install -r requirements.txt
```

### Run the Backend Server
```bash
cd /home/lade/Hackathons/network-guardian-ai/backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run All Tests
```bash
cd /home/lade/Hackathons/network-guardian-ai
PYTHONPATH=. python -m pytest backend/tests/ -v
```

### Run a Single Test
```bash
cd /home/lade/Hackathons/network-guardian-ai
PYTHONPATH=. python -m pytest backend/tests/test_heuristics.py::test_entropy_logic -v
PYTHONPATH=. python -m pytest backend/tests/test_router.py::test_health_endpoint -v
```

### Run Tests with Coverage
```bash
cd /home/lade/Hackathons/network-guardian-ai/backend
pytest backend/tests/ -v --cov=backend --cov-report=term-missing
```

### Linting (ruff)
```bash
ruff check backend/
ruff check backend/ --fix
```

### Type Checking (mypy)
```bash
mypy backend/ --ignore-missing-imports
```

## Project Structure
```
backend/
├── api/           # FastAPI routes and models
├── core/          # Config, state, utilities
├── logic/         # ML heuristics, anomaly detection, vector store
├── services/      # External integrations (AdGuard, Gemini, Sheets)
├── tests/         # Unit and integration tests
├── main.py        # Application entry point
└── system_intelligence.py  # System status display
```

## Code Style Guidelines

### Imports
- Use absolute imports: `from backend.logic.ml_heuristics import ...`
- Group imports: stdlib, third-party, local
- Sort alphabetically within groups
```python
import os
import time
from datetime import datetime

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.config import settings
from backend.services.gemini_analyzer import analyze_domain
```

### Formatting
- Line length: 100 characters max
- Use 4 spaces for indentation (no tabs)
- Use blank lines to separate logical sections (2 for top-level, 1 for functions)
- Trailing commas in multi-line structures

### Types
- Use Python 3.10+ type hints throughout
- Prefer explicit types over `Any`
- Use `Optional[X]` instead of `X | None` for compatibility
- Add return types to all functions
```python
def calculate_entropy(domain: str) -> float:
    ...
```

### Naming Conventions
- **Files**: snake_case (e.g., `ml_heuristics.py`, `adguard_poller.py`)
- **Classes**: PascalCase (e.g., `AnomalyEngine`, `VectorMemory`)
- **Functions/variables**: snake_case (e.g., `calculate_entropy`, `processed_domains`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `POLL_INTERVAL`)
- **Private methods**: prefix with underscore (e.g., `_heuristic_fallback`)

### Error Handling
- Use try/except with specific exception types
- Always log errors before re-raising or returning fallbacks
- Implement graceful degradation (return sensible defaults on failure)
- Never expose raw exception messages to API responses
```python
try:
    analysis = analyze_domain(domain, context)
except Exception as e:
    print(f"Analysis Failed: {e}")
    return _heuristic_fallback(domain, str(e))
```

### API Design
- All endpoints return JSON
- Use Pydantic models for request/response validation
- Include appropriate HTTP status codes (200, 401, 429, 500)
- Add docstrings to all endpoints

### Database/State
- Use in-memory collections for session state (lists, dicts)
- Google Sheets is the persistence layer (not a database)
- Implement circuit breakers for external API failures

### Testing
- Write tests for all new functions in `backend/tests/`
- Use `pytest` as the test framework
- Mock external services (Gemini API, AdGuard, Sheets)
- Include both unit tests (logic) and integration tests (API endpoints)

### Security
- Never log API keys or credentials
- Validate all user inputs (especially domain names)
- Use `is_valid_domain()` before processing input
- Keep secrets in `.env` files, never commit them

### Specific Patterns Used in This Project

1. **Singleton Pattern**: Global instances (e.g., `engine`, `classifier`, `vector_memory`)
2. **Circuit Breaker**: Fallback to heuristics when cloud APIs fail
3. **RAG-lite**: Hash-based "embeddings" in vector store (not actual ML)
4. **BFF Pattern**: Backend-for-Frontend centralizes API logic

## Known Issues / Limitations
- The "vector store" uses SHA256 hashing, not actual embeddings
- Isolation Forest needs 5+ samples before it can detect anomalies
- Frontend React code exists but requires building separately
- Empty `backend/api/chat.py` file exists (functionality is in `router.py`)
