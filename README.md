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
