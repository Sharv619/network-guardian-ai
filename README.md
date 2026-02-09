***

# 🛡️ Network Guardian AI: Project Antigravity
### *Autonomous Network Threat Intelligence & Behavioral Audit Pipeline*

---

## 📖 Table of Contents
1. [🔍 Overview](#-overview)
2. [🕹️ Core Features](#-core-features)
3. [🏗️ System Architecture](#-system-architecture)
4. [🧠 Intelligence Layers](#-intelligence-layers)
5. [⚙️ Reliability & SRE Design](#-reliability--sre-design)
6. [🚦 Getting Started](#-getting-started)
7. [🧪 Technical Verification](#-technical-verification)

---

## 🔍 Overview
Network Guardian AI is a real-time security operations tool that unmasks hidden network telemetry. It intercepts background DNS requests, performs multi-layered behavioral and semantic analysis, and logs verdicts into a cloud-hosted audit trail. The system transforms cryptic logs into human-readable intelligence, identifying everything from standard tracking pixels to stealthy geolocation exfiltration attempts.

---

## 🕹️ Core Features
*   **Live Threat Feed**: A real-time stream of network requests with color-coded risk assessments and pulsing alerts for privacy violations.
*   **Manual Domain Audit**: An investigative laboratory for on-demand analysis of specific domains using multiple AI models.
*   **Privacy Radar**: Specialized detection logic that flags background geolocation pings and telemetry spikes.
*   **Cloud Data Lake**: Automatic synchronization of every security verdict to Google Sheets for permanent record-keeping and mobile access.
*   **System Awareness Chat**: A technical agent capable of explaining the current network state and underlying architecture.

---

## 🏗️ System Architecture
The platform is deployed as a consolidated, multi-stage Docker environment.

*   **Network Interceptor**: AdGuard Home (Intercepts DNS queries at the source).
*   **Orchestration Engine**: Python 3.12 / FastAPI (Handles data polling and model coordination).
*   **Persistence Layer**: Google Sheets API v4 (Provides a shared, immutable system of record).
*   **Dashboard UI**: React / TypeScript / Tailwind CSS (Provides real-time observability).

---

## 🧠 Intelligence Layers
Security verdicts are determined through a three-stage "Defense in Depth" pipeline:

| Layer | Method | Purpose |
| :--- | :--- | :--- |
| **Layer 1** | Shannon Entropy (Base 2) | Detects random-looking DGA (Domain Generation Algorithm) strings locally. |
| **Layer 2** | Isolation Forest (ML) | An unsupervised model that identifies structural outliers in network traffic. |
| **Layer 3** | Google Gemini 3 (AI) | Performs high-level semantic reasoning to explain the threat in plain English. |

---

## ⚙️ Reliability & SRE Design
The system is built to maintain 100% network observability through professional-grade patterns:

*   **Circuit Breakers**: If cloud APIs are throttled or unreachable, the system automatically falls back to local heuristic math to maintain protection.
*   **BFF Pattern**: The Backend-for-Frontend pattern centralizes all secrets and AI logic, ensuring API keys never leak to the client browser.
*   **FinOps Logic**: Just-In-Time (JIT) context injection minimizes token usage by only sending system documentation to the AI when relevant.
*   **Standardization**: All telemetry uses ISO-8601 UTC timestamps for accurate cross-system log correlation.

---

## 🚦 Getting Started

### 1. Environment Configuration
Create a `.env` file in the root directory with the following variables:
```bash
GEMINI_API_KEY='your_api_key'
GOOGLE_SHEET_ID='your_spreadsheet_id'
GOOGLE_SHEETS_CREDENTIALS='{ "type": "service_account", ... }'
ADGUARD_USER='admin'
ADGUARD_PASS='password'
ADGUARD_URL='http://172.17.0.1:8080'
```

### 2. Deployment
Build and launch the stack using Docker Compose:
```bash
docker compose up -d --build
```

### 3. Access
*   **Guardian Dashboard**: `http://localhost:8000`
*   **AdGuard Management**: `http://localhost:8080`

---

## 🧪 Technical Verification
The system includes a suite of automated tests to verify mathematical logic and API resilience.

**Run Logic Tests:**
```bash
docker exec network-guardian pytest backend/tests/ -v
```
**Current Coverage:**
*   Shannon Entropy Accuracy (Base 2 Math)
*   URL Sanitization & Regex Performance
*   API Circuit Breaker & Fallback Veracity
*   Data Serialization Consistency

---

**Built for the Google Gemini 3 Hackathon 2026.** 🛡️📊🚀🏁
