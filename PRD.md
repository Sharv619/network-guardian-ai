# Network Guardian AI - Product Requirements Document (PRD)

## 1. Overview

**Project Name:** Network Guardian AI  
**Type:** Network Security Monitoring & Threat Detection System  
**Core Functionality:** Intercepts DNS requests via AdGuard Home, analyzes domains using Gemini AI and local ML heuristics (Shannon Entropy, Isolation Forest), and logs results to Google Sheets.  
**Target Users:** Home users, small businesses, security enthusiasts who run AdGuard Home for network-wide ad/tracker blocking.

---

## 2. Problem Statement

- Users with AdGuard Home have no visibility into what domains are being blocked and why
- Manual review of DNS logs is time-consuming and requires security expertise
- No automated threat intelligence or pattern learning from network traffic
- Lack of centralized logging and historical analysis of network threats

---

## 3. Goals & Objectives

### Primary Goals
1. **Automate Threat Detection** - Analyze every DNS query automatically without user intervention
2. **Reduce Cloud API Costs** - Use local ML heuristics as first-line defense, only escalating to Gemini AI when necessary
3. **Learn Over Time** - Build pattern database from AdGuard metadata to reduce external API dependency
4. **Persist Everything** - Log all analysis results to Google Sheets for audit and historical analysis

### Success Metrics
- Autonomy Score: % of domains classified locally (without Gemini)
- Cache Hit Rate: % of domains served from cache
- Zero-day Detection: Anomalies flagged by Isolation Forest
- Time to Analysis: <2s per domain

---

## 4. User Personas

| Persona | Description | Needs |
|---------|-------------|-------|
| **Home User** | Runs AdGuard for family network protection | Simple dashboard, automated alerts |
| **Security Hobbyist** | Wants to learn about network threats | Detailed analysis, chat with AI |
| **Small Business IT** | Protects small office network | Audit logs, threat history |

---

## 5. Functional Requirements

### 5.1 DNS Polling
- Poll AdGuard Home querylog API at configurable interval (default: 30s)
- Handle authentication (username/password)
- Fallback to multiple AdGuard URLs if primary fails
- Deduplicate domains to avoid repeated analysis

### 5.2 Domain Analysis Pipeline
- **Tier 1:** Check analysis cache (memory + disk)
- **Tier 2:** Check metadata classifier (local pattern matching)
- **Tier 3:** Run ML heuristics (entropy, digit ratio)
- **Tier 4:** Run Isolation Forest anomaly detection
- **Tier 5:** Escalate to Gemini AI for full analysis

### 5.3 Privacy & Tracker Detection
- Auto-escalate domains containing privacy keywords (geo, location, gps, telemetry)
- Auto-flag tracker domains (pixel, metrics, collect)
- High entropy (>3.8) triggers malware classification

### 5.4 Anomaly Detection
- Train Isolation Forest on domain features (entropy, length, digit ratio, vowel ratio)
- Requires minimum 10 samples before prediction
- Flag domains with anomaly score < -0.1

### 5.5 Pattern Learning
- Learn from completed Gemini analyses
- Build metadata patterns (reason, filter_id, rule, client)
- Seed with pre-learned patterns (Google, Microsoft telemetry, malware)
- Persist patterns to disk (metadata_patterns.json)

### 5.6 Persistence
- Log all threats to Google Sheets
- Columns: timestamp, domain, risk_score, category, summary, AdGuard metadata, anomaly score
- Fetch recent history with 30s cache to avoid quota limits

### 5.7 Chat Interface
- Conversational interface to query the AI
- Fallback to local heuristics if Gemini rate-limited

### 5.8 Manual Analysis
- Allow users to manually submit domains for analysis
- Same pipeline as automated analysis

---

## 6. Non-Functional Requirements

### 6.1 Performance
- Analysis latency: <2s per domain (cached: <10ms)
- Polling interval: configurable (default 30s, min 5s)
- Cache TTL: 5min (memory), 1hr (disk)

### 6.2 Scalability
- In-memory deduplication for 5000 domains
- Anomaly engine history: 10000 samples max

### 6.3 Reliability
- Circuit breaker pattern for external APIs
- Graceful degradation to local heuristics on failure
- Background cleanup of expired cache entries

### 6.4 Security
- Validate domain format before processing
- Never log API keys or credentials
- CORS configured for localhost origins only

---

## 7. Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  AdGuard Home   │────▶│  Backend (FastAPI) │────▶│ Google Sheets  │
│  (DNS Logs)     │     │                  │     │ (Persistence)   │
└─────────────────┘     │  ┌─────────────┐ │     └─────────────────┘
                        │  │   Poller    │ │
                        │  └─────────────┘ │
                        │         ▼        │
                        │  ┌─────────────┐ │
                        │  │    Cache    │ │
                        │  └─────────────┘ │
                        │         ▼        │
                        │  ┌─────────────┐ │
                        │  │  Heuristics │ │
                        │  │  (Entropy)  │ │
                        │  └─────────────┘ │
                        │         ▼        │
                        │  ┌─────────────┐ │
                        │  │ Anomaly Eng │ │
                        │  │(IsolationFr)│ │
                        │  └─────────────┘ │
                        │         ▼        │
                        │  ┌─────────────┐ │
                        │  │  Metadata   │ │
                        │  │ Classifier  │ │
                        │  └─────────────┘ │
                        │         ▼        │
                        │  ┌─────────────┐ │
                        │  │   Gemini    │ │
                        │  │    API      │ │
                        │  └─────────────┘ │
                        └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   React Frontend │
                        │   (Dashboard,    │
                        │   Chat, Modals)  │
                        └──────────────────┘
```

---

## 8. Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python) |
| ML | Scikit-learn (Isolation Forest) |
| AI | Google Gemini API |
| Database | Google Sheets (persistence), In-memory (cache) |
| DNS | AdGuard Home API |
| Frontend | React + TypeScript |
| Auth | AdGuard credentials, Google Service Account |

---

## 9. Data Flow

1. **Poller** fetches DNS logs from AdGuard every N seconds
2. **Deduplication** - skip already-processed domains
3. **Cache Check** - return cached result if available
4. **Feature Extraction** - calculate entropy, digit ratio, etc.
5. **Anomaly Detection** - Isolation Forest predicts outlier
6. **Metadata Classification** - local pattern match
7. **Gemini Escalation** - if needed, call AI API
8. **Vector Memory** - store for similarity search
9. **Sheets Logging** - persist to Google Sheets
10. **State Update** - push to in-memory buffer for API

---

## 10. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/threats` | Get automated threats |
| GET | `/api/threats/manual` | Get manual scans |
| POST | `/api/analyze` | Manual domain analysis |
| GET | `/api/history` | Recent history from Sheets |
| POST | `/api/chat` | Chat with AI |
| GET | `/api/system/stats` | System intelligence stats |
| GET | `/api/models` | Available Gemini models |

---

## 11. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API Key |
| `GOOGLE_SHEETS_CREDENTIALS` | Yes | Service Account JSON |
| `GOOGLE_SHEET_ID` | Yes | Target Sheet ID |
| `ADGUARD_URL` | No | AdGuard Home URL |
| `ADGUARD_USER` | No | AdGuard Username |
| `ADGUARD_PASS` | No | AdGuard Password |
| `POLL_INTERVAL` | No | Polling interval (default: 30) |
| `NOTION_TOKEN` | No | Notion API Token |
| `NOTION_DATABASE_ID` | No | Notion Database ID |

---

## 12. Security

- Domain validation (no spaces, must contain dot)
- No credential logging
- CORS restricted to localhost
- Pydantic input validation on all endpoints

---

## 13. Known Limitations

- Vector store uses SHA256 hashing, not real embeddings
- Isolation Forest needs 10+ samples before detecting anomalies
- Frontend requires separate build
- Notion integration is optional

---

## 14. Future Roadmap

- [ ] Real embeddings via Gemini Embeddings API
- [ ] Multi-network support (multiple AdGuard instances)
- [ ] Real-time WebSocket notifications
- [ ] Email/Slack alerts for high-risk threats
- [ ] Dashboard charts and visualizations
- [ ] Export to CSV/PDF
- [ ] User authentication for frontend