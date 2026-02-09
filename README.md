# 🛡️ Network Guardian AI: Project Antigravity
### *Autonomous Network Threat Intelligence & Behavioral Audit Pipeline*

---

## 📖 Table of Contents
1. [🔍 Overview](#-overview)
2. [🕹️ Core Features](#-core-features)
3. [🏗️ System Architecture](#-system-architecture)
4. [🧠 Intelligence Layers](#-intelligence-layers)
5. [📊 Google Sheets Integration](#-google-sheets-integration)
6. [⚙️ Reliability & SRE Design](#-reliability--sre-design)
7. [🚦 Getting Started](#-getting-started)
8. [🧪 Technical Verification](#-technical-verification)
9. [🎨 Enhanced UI Components](#-enhanced-ui-components)

---

## 🔍 Overview
Network Guardian AI is a real-time security operations tool that unmasks hidden network telemetry. It intercepts background DNS requests, performs multi-layered behavioral and semantic analysis, and logs verdicts into a cloud-hosted audit trail. The system transforms cryptic logs into human-readable intelligence, identifying everything from standard tracking pixels to stealthy geolocation exfiltration attempts.

Built with a Production-First mindset, this system provides enterprise-grade reliability while maintaining accessibility for personal use.

---

## 🕹️ Core Features
*   **Live Threat Feed**: A real-time stream of network requests with color-coded risk assessments and pulsing alerts for privacy violations.
*   **Manual Domain Audit**: An investigative laboratory for on-demand analysis of specific domains using multiple AI models.
*   **Privacy Radar**: Specialized detection logic that flags background geolocation pings and telemetry spikes.
*   **Cloud Data Lake**: Automatic synchronization of every security verdict to Google Sheets for permanent record-keeping and mobile access.
*   **System Awareness Chat**: A technical agent capable of explaining the current network state and underlying architecture.
*   **Enhanced AnalysisModal**: Comprehensive domain analysis with Google Sheets integration details and historical insights.

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

## 📊 Google Sheets Integration
### Real-Time Threat Synchronization
Every domain analysis is automatically logged to Google Sheets with comprehensive metadata:

**Data Fields Logged:**
- Domain name and classification
- Risk assessment (Low/Medium/High/Critical)
- Category (Tracker/System/Advertising/Malware/etc.)
- AI-generated summary and reasoning
- Anomaly detection scores
- Timestamp and analysis method

**Integration Features:**
- **Real-time synchronization**: Domains like `rr8---sn-v2u0n-hxad.googlevideo.com` are logged immediately
- **Error handling**: Robust retry mechanisms and fallback logging
- **Mobile access**: View security audit trail from any device
- **Historical analysis**: Track threat patterns over time

**Example Log Entry:**
```
Domain: rr8---sn-v2u0n-hxad.googlevideo.com
Category: System/Tracker
Risk Score: High
Summary: YouTube video streaming domain - legitimate but tracks viewing behavior
Anomaly Score: 0.0537
Timestamp: 2026-10-02T09:08:15Z
```

---

## ⚙️ Reliability & SRE Design
The system is built to maintain 100% network observability through professional-grade patterns:

*   **Circuit Breakers**: If cloud APIs are throttled or unreachable, the system automatically falls back to local heuristic math to maintain protection.
*   **BFF Pattern**: The Backend-for-Frontend pattern centralizes all secrets and AI logic, ensuring API keys never leak to the client browser.
*   **FinOps Logic**: Just-In-Time (JIT) context injection minimizes token usage by only sending system documentation to the AI when relevant.
*   **Standardization**: All telemetry uses ISO-8601 UTC timestamps for accurate cross-system log correlation.
*   **Graceful Degradation**: System continues operating with local analysis if cloud services are unavailable.

---

## 🎨 Enhanced UI Components
### AnalysisModal Improvements
The AnalysisModal has been enhanced with a comprehensive 4-column layout:

1. **System Intelligence**: Displays autonomy score, local vs cloud decisions, and pattern counts
2. **Cache Performance**: Shows memory cache status, valid entries, and disk cache information
3. **System Usage Details**: Active integrations, tracker detection statistics, and learning progress
4. **Google Sheets Integration**: Real-time synchronization status, total records, and domain-specific insights

**Key Features:**
- Professional dark theme with cyberpunk aesthetic
- Real-time data visualization
- Domain-specific analysis examples (e.g., googlevideo.com)
- Historical context and trend analysis

---

## 🚦 Getting Started

### 1. Environment Configuration
Create a `.env` file in the root directory with the following variables:
```bash
GEMINI_API_KEY='your_google_ai_studio_key'
GOOGLE_SHEET_ID='your_spreadsheet_id'
GOOGLE_SHEETS_CREDENTIALS='{ "type": "service_account", ... }'
ADGUARD_USER='admin'
ADGUARD_PASS='admin12345'
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
*   Google Sheets Integration Error Handling
*   Anomaly Detection Algorithm Validation

---

## 🤝 Open Source & Contributions
This project is open-source and built with passion. It provides tools for digital sovereignty and network transparency.

**Key Technologies:**
- **AI/ML**: Google Gemini 3, Scikit-Learn (Isolation Forest), Shannon Entropy
- **Backend**: Python 3.12, FastAPI, Docker
- **Frontend**: React, TypeScript, Tailwind CSS
- **Integration**: Google Sheets API v4, AdGuard Home

**Built for the Google Gemini 3 Hackathon 2026.** 🛡️📊🚀🏁

---

## 📈 Current System Status
- ✅ **20+ historical records** in the system
- ✅ **Google Sheets integration** active and logging domains
- ✅ **Enhanced AnalysisModal** displaying Google Sheets data
- ✅ **Real-time threat detection** and logging working
- ✅ **System serving** on http://localhost:8000
- ✅ **Multi-layered intelligence** pipeline operational

The system successfully detects and logs domains like `rr8---sn-v2u0n-hxad.googlevideo.com` with comprehensive analysis including risk scores, anomaly detection, and AI-generated explanations.