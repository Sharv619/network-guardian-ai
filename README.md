<<<<<<< HEAD
***
=======
🛡️ Network Guardian AI: Project Antigravity
Autonomous Threat Intelligence & Behavioral Anomaly Detection

![alt text](https://img.shields.io/badge/AI-Google%20Gemini%203-blueviolet) ![alt text](https://img.shields.io/badge/Architecture-SRE--Engineered-success) ![alt text](https://img.shields.io/badge/Security-BFF--Pattern-red) ![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)

🧠 The "Why"

"Is it freedom or loneliness?" I built Network Guardian AI during a career break to answer a single question: Why does my phone feel like a spy?

As a former social media manager, I saw the tracking side of the industry from the inside. As an engineer who once worked a delivery job to pay rent while managing production servers, I learned that Reliability is a requirement for survival. This project is the culmination of those "war scars"—a tool that turns a "lonely" black box of network logs into a transparent, AI-powered audit trail.
🚀 The Vision: Moving from Reactive to Proactive

Most firewalls just block a domain because a static list told them to. Network Guardian AI gives your network a Brain. It doesn't just block; it explains, learns, and remembers.
1. Intercept (The Eyes)

DNS-level interception via AdGuard Home catches every background request your phone or IoT devices make.
2. Behavioral ML (The Intuition)

A local Isolation Forest model (Unsupervised Machine Learning) analyzes the structural patterns of every domain. It identifies "Zero-Day" anomalies that haven't even hit global blocklists yet based on their statistical "weirdness."
3. Gemini 3 Reasoning (The Analyst)

Google Gemini 3 acts as a senior SOC Analyst. Using its advanced reasoning, it interprets the local ML scores and provides human-readable context: "This domain is a legitimate Google service" vs "This is a stealthy geolocation tracking attempt."
4. Cloud Ledger (The Memory)

Verdicts are streamed live to a Google Sheets Data Lake via IAM-secured Service Accounts, providing a permanent, mobile-accessible security audit trail.
🛠️ The "Guardian" Stack

    AI/ML: Google Gemini 3 (Flash & Pro), Scikit-Learn (Isolation Forest), Shannon Entropy heuristics.

    Orchestrator: Python 3.12, FastAPI (Asynchronous Data Pipeline).

    Infrastructure: Docker Compose (Multi-container orchestration), Linux Bridge Networking.

    Persistence: Google Sheets API v4 (Google Ecosystem Integration).

    Observability: React + TypeScript Dashboard with real-time "Heartbeat" monitoring.

⚙️ SRE & Reliability Pillars

This project was built with a Production-First mindset, focusing on high-paying SRE skills:

    BFF (Backend-for-Frontend) Pattern: Secured API secrets by centralizing all AI logic in the backend. The browser never sees the keys.

    Circuit Breaker Logic: If the Gemini API is throttled (429 Error), the system gracefully degrades to "Autonomous SOC Mode," using local Shannon Entropy math to maintain network protection without the cloud.

    FinOps Optimization: Implemented JIT (Just-In-Time) Context Injection, reducing token burn by 70% by only sending system documentation to the AI when architecturally relevant.

    Continuous Verification: 100% logic coverage via an automated Pytest suite that validates mathematical entropy and API failover resilience.

🚦 Getting Started
1. Configuration

Create a .env file in the root directory:
code Bash

GEMINI_API_KEY='your_google_ai_studio_key'
GOOGLE_SHEET_ID='your_spreadsheet_id'
GOOGLE_SHEETS_CREDENTIALS='{"type": "service_account", ...}' # Minified JSON string
ADGUARD_USER='admin'
ADGUARD_PASS='admin12345'
ADGUARD_URL='http://172.17.0.1:8080' # Host Gateway for Linux

2. Deploy
code Bash

docker compose up -d --build

3. Verify Logic
code Bash

docker exec network-guardian pytest backend/tests/

📂 Project Structure

    backend/logic/ml_heuristics.py: Shannon Entropy & Input Sanitization.

    backend/logic/anomaly_engine.py: Isolation Forest Unsupervised Learning.

    backend/services/gemini_analyzer.py: XAI (Explainable AI) & Circuit Breaker logic.

    frontend/components/Dashboard.tsx: Real-time Observability & Privacy Radar.

🤝 Open Source

"Isolation is the gift." — Charles Bukowski.
This project is open-source. Use it to watch the watchers. Take your digital sovereignty back.

Built for the Google Gemini 3 Hackathon 2026. 🛡️📊🚀🏁
>>>>>>> 09d5fb4 (finalising readme)

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
