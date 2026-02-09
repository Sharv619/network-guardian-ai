🛡️ Network Guardian AI: Project Antigravity
An Automated Threat Intelligence Pipeline powered by Google Gemini & Behavioral ML

![alt text](https://img.shields.io/badge/AI-Google%20Gemini-blue)


![alt text](https://img.shields.io/badge/Architecture-SRE--Ready-green)


![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)

🧠 The "Why"

"Is it freedom or loneliness?" I built this project during a career break to answer a simple question: Why does my phone feel like a spy?

As a former social media manager, I’ve seen the "tracking" side of the industry. As an engineer who once worked a delivery job to pay rent while managing production servers at 2 AM, I learned that you cannot afford a single point of failure.

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
