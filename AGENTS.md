# AGENTS.md - Network Guardian AI

## Overview

This is a FastAPI-based network security tool that intercepts DNS requests via AdGuard, analyzes domains using Gemini AI and local ML heuristics (Shannon Entropy, Isolation Forest), and logs results to Google Sheets. The system features real-time WebSocket communication, enhanced dashboard with live statistics, and optimized performance.

## Build & Run Commands

### Install Dependencies
```bash
# Backend
cd /home/lade/Hackathons/network-guardian-ai/backend
pip install -r requirements.txt

# Frontend  
cd ../frontend
npm install

# Optional: sentence-transformers for vector embeddings
pip install sentence-transformers
```

### Run the Backend Server
```bash
cd /home/lade/Hackathons/network-guardian-ai
PYTHONPATH=. python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run the Frontend Development Server
```bash
cd /home/lade/Hackathons/network-guardian-ai/frontend
npm run dev
```

### Build the Frontend
```bash
cd /home/lade/Hackathons/network-guardian-ai/frontend
npm run build
```

### Run All Tests
```bash
cd /home/lade/Hackathons/network-guardian-ai
PYTHONPATH=. python -m pytest Tests_AI/ -v
```

### Run a Single Test
```bash
cd /home/lade/Hackathons/network-guardian-ai
PYTHONPATH=. python -m pytest Tests_AI/test_heuristics.py::test_entropy_logic -v
PYTHONPATH=. python -m pytest Tests_AI/test_router.py::test_health_endpoint -v
```

### Run Tests with Coverage
```bash
cd /home/lade/Hackathons/network-guardian-ai
PYTHONPATH=. pytest Tests_AI/ -v --cov=backend --cov-report=term-missing
```

### Linting (ruff)
```bash
cd /home/lade/Hackathons/network-guardian-ai
ruff check backend/
ruff check backend/ --fix
```

### Type Checking (mypy)
```bash
cd /home/lade/Hackathons/network-guardian-ai
mypy backend/ --ignore-missing-imports
```

### MCP Server (for AI agent integration)
```bash
# Run the MCP server
python mcp_server.py

# Or use the simpler version
python network_guardian_mcp.py
```

## Project Structure
```
backend/
├── api/              # FastAPI routes (chat.py, router.py, stats.py, etc.)
├── core/             # Config, state, auth, websocket manager
├── db/               # SQLAlchemy models, repository, database
├── logic/            # ML heuristics, anomaly detection, vector store, embeddings
├── services/         # External integrations (AdGuard, Gemini, Sheets)
├── main.py           # Application entry point
└── system_intelligence.py

Tests_AI/            # Unit and integration tests
frontend/
├── src/
│   ├── services/     # WebSocket service, API services
│   ├── components/  # React components (Dashboard, StatsPanel, etc.)
│   └── hooks/       # Custom React hooks
├── components/      # Shared React components
└── types.ts         # TypeScript type definitions
```

## Code Style Guidelines

### Imports
- Use absolute imports: `from backend.logic.ml_heuristics import ...`
- Group imports in order: stdlib, third-party, local
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
except SpecificException as e:
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
- Use SQLite via SQLAlchemy for persistence
- Use repository pattern for database operations

### Testing
- Write tests for all new functions in `Tests_AI/`
- Use `pytest` as the test framework
- Mock external services (Gemini API, AdGuard, Sheets)
- Include both unit tests (logic) and integration tests (API endpoints)

### Security
- Never log API keys or credentials
- Validate all user inputs (especially domain names)
- Use `is_valid_domain()` before processing input
- Keep secrets in `.env` files, never commit them

## Key Features

### 1. Real-time DNS Analysis
- AdGuard DNS interception
- Shannon Entropy for DGA detection
- Isolation Forest for anomaly detection
- Gemini AI for domain classification

### 2. Vector Store & RAG
- SQLAlchemy persistence with float32 embeddings
- Hybrid search (semantic + keyword)
- RAG context builder for chatbot

### 3. Conversational Chatbot
- Short responses for simple queries (<=3 words)
- Full analysis for domain-specific queries
- Real-time system stats integration
- Keyword-based intent recognition

### 4. WebSocket Integration
- Multiple endpoints: `/ws`, `/ws/public`, `/ws/admin`
- Real-time threat updates
- Connection status indicators

## Environment Variables

Key environment variables (see `.env`):
```bash
# API Keys
GEMINI_API_KEY=your_key_here
NOTION_TOKEN=your_token
GOOGLE_SHEETS_CREDENTIALS=json_credentials
GOOGLE_SHEET_ID=spreadsheet_id

# AdGuard
ADGUARD_URL=http://localhost:8080
ADGUARD_USER=admin
ADGUARD_PASS=password

# Ollama (optional)
OLLAMA_ENABLED=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2

# Embedding Provider
EMBEDDING_PROVIDER=sentence-transformers  # or "ollama", "mock"
```

## Known Issues
- Isolation Forest needs 10+ samples before detecting anomalies
- sentence-transformers not installed by default (run: `pip install sentence-transformers`)
- Gemini API has rate limits - falls back to heuristics when exceeded
