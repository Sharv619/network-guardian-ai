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
=======

# 🛡️ Network Guardian AI: Project Antigravity

An Automated Threat Intelligence Pipeline powered by Google Gemini & Behavioral ML

![alt text](https://img.shields.io/badge/AI-Google%20Gemini-blue)


![alt text](https://img.shields.io/badge/Architecture-SRE--Ready-green)


![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)

🧠 The "Why"

"Is it freedom or loneliness?" I built this project during a career break to answer a simple question: Why does my phone feel like a spy?

As a former social media manager, I've seen the "tracking" side of the industry. As an engineer who once worked a delivery job to pay rent while managing production servers at 2 AM, I learned that you cannot afford a single point of failure.

Network Guardian AI is a passion project born from the necessity of sovereignty. It turns your network's "lonely" black box of logs into a transparent, AI-powered audit trail.
🚀 Vision: From "Dumb Logs" to "Explainable AI"

Most firewalls just block a domain because a list told them to. Network Guardian AI gives your network a Brain.

    Intercept: DNS-level blocking via AdGuard Home.

    Filter: Local Shannon Entropy math detects random "Malware-looking" domains (DGA) instantly.

    Learn: An unsupervised Isolation Forest (Machine Learning) model identifies behavioral anomalies on your network.

    Reason: Google Gemini 1.5 Flash acts as a SOC Analyst, providing a human-readable "Why" for every threat.

    Persist: Verdicts are streamed live to a Google Sheets Data Lake for a permanent security audit.

🛠️ Tech Stack

    AI/ML: Google Gemini 1.5 Flash, Scikit-Learn (Isolation Forest), Shannon Entropy (Heuristics).

    Backend: Python 3.12, FastAPI.

    Frontend: React, Tailwind CSS (Hacker-style UI).

    Database: Google Sheets API (Google Ecosystem Integration).

    Infrastructure: Docker Compose, Linux Bridge Networking.

⚙️ SRE & Security Architecture

This project was built with a Production-First mindset:

    BFF (Backend-for-Frontend) Pattern: AI API keys are hidden in the backend; the browser never sees them.

    Graceful Degradation: If the Gemini API is throttled (429), a Circuit Breaker triggers local Heuristic analysis so the network remains guarded.

    Observability: Integrated "Heartbeat" status indicators and standardized ISO-8601 time-series logging.

    Continuous Verification: Automated Pytest suite validating mathematical logic and API resilience.

🚦 Getting Started
1. Prerequisites

    Google AI Studio Key: Get a Gemini API Key

    Google Cloud Service Account: Create a service account, download the JSON key, and share your Google Sheet with the service account email.

    AdGuard Home: Running via Docker (included in stack).

2. Configure Environment

Create a .env file:
code Bash

GEMINI_API_KEY='your_key'
GOOGLE_SHEET_ID='your_spreadsheet_id'
GOOGLE_SHEETS_CREDENTIALS='{"type": "service_account", ...}' # Single-line minified JSON
ADGUARD_USER='admin'
ADGUARD_PASS='admin12345'
ADGUARD_URL='http://172.17.0.1:8080' # Host Gateway for Linux

3. Deploy the Stack
code Bash

docker compose up -d --build

4. Run the Reliability Tests
code Bash

docker exec network-guardian pytest backend/tests/

📂 Project Logic

    backend/logic/ml_heuristics.py: Shannon Entropy & URL Sanitization.

    backend/logic/anomaly_engine.py: Isolation Forest Unsupervised Learning.

    backend/services/gemini_analyzer.py: Explainable AI (XAI) & Circuit Breaker logic.

    backend/services/sheets_logger.py: Google Sheets Persistence Layer.

🤝 Open Source & Contributions

This project is Vibe-Coded—built with passion, curiosity, and a lot of late nights. It is open-source because I believe everyone should have the tools to watch the watchers.

Feel free to fork, modify, and build your own Guardian.

"Isolation is the gift." — Charles Bukowski
>>>>>>> 09d5fb4a61b269a7e9f329a0a76cab6ce114d0bb
