***

# 🛡️ Network Guardian AI: Project Antigravity
### *The Autonomous Threat Intelligence & Privacy Audit Pipeline*

---

## 📖 Table of Contents
1. [🧠 The Vision & Origin Story](#-the-vision--origin-story)
2. [🚀 Core Mission: Watching the Watchers](#-core-mission-watching-the-watchers)
3. [🏗️ Technical Architecture](#-technical-architecture)
4. [🧠 Intelligence Layers (Heuristics & ML)](#-intelligence-layers-heuristics--ml)
5. [⚙️ SRE & Reliability Pillars](#-sre--reliability-pillars)
6. [📊 Google Ecosystem Integration](#-google-ecosystem-integration)
7. [🚦 Getting Started](#-getting-started)
8. [🧪 Automated Verification](#-automated-verification)
9. [👤 About the Architect](#-about-the-architect)

---

## 🧠 The Vision & Origin Story
**"Is it freedom or loneliness?"** I built Network Guardian AI during a career break to solve a personal technical debt: the lack of transparency in home network traffic.

Born from the observation that our devices are constantly "leaking" telemetry and location data behind our backs—often triggered by private conversations—this project moves network defense from **passive blocking** to **active intelligence**.

---

## 🚀 Core Mission: Watching the Watchers
Most firewalls are "silent killers"—they block a domain without explaining why. Project Antigravity provides:
*   **Contextual Clarity**: Every blocked packet is analyzed by AI to explain its intent.
*   **Privacy Interception**: Specific detection for background Geolocation exfiltration.
*   **Behavioral Learning**: Identifying "Zero-Day" anomalies through statistical outliers.
*   **Sovereign Logging**: A live, cloud-hosted ledger of every tracking attempt.

---

## 🏗️ Technical Architecture
The system is built as a **Consolidated Monolithic Container**, minimizing latency and simplifying the "DevOps Tax" of distributed systems.

*   **Interceptor**: [AdGuard Home](https://adguard.com/en/adguard-home/overview.html) (Dockerized DNS Sinkhole).
*   **Orchestrator**: Python 3.12 + FastAPI (Async Polling Engine).
*   **Frontend**: React 18 + TypeScript + Tailwind CSS (Hacker-style UI).
*   **Database**: Google Sheets API v4 (Live Data Lake).
*   **Containerization**: Docker Compose with custom bridge networking.

---

## 🧠 Intelligence Layers (Heuristics & ML)
We implement **Defense in Depth** through three distinct layers of analysis:

### Layer 1: Shannon Entropy (Local Heuristics)
Using the **Shannon Entropy (Base 2)** formula with a custom **Digit-Ratio Penalty**, the system identifies DGA (Domain Generation Algorithms) used by malware.
> *SRE Logic: This layer runs in microseconds and requires zero API calls, serving as our high-speed filter.*

### Layer 2: Isolation Forest (Unsupervised ML)
We utilize **Scikit-Learn's Isolation Forest** to learn the "Normal" character distribution of your network. Domains that are statistical outliers are flagged as **ZERO-DAY SUSPECTS**.

### Layer 3: Google Gemini 3 (Reasoning)
**Gemini 1.5 Flash** acts as our Senior SOC Analyst. It receives the raw domain metadata + ML scores and generates a human-readable forensic summary.

---

## ⚙️ SRE & Reliability Pillars
Engineered for **survival**, not just for the demo:

*   **Circuit Breaker Pattern**: If the Gemini API returns a 429 (Resource Exhausted), the system gracefully degrades to **"Autonomous SOC Mode,"** using local heuristics to maintain protection.
*   **BFF (Backend-for-Frontend)**: All API keys and cloud logic are strictly server-side. The browser never touches a secret.
*   **JIT (Just-In-Time) Context**: To optimize FinOps, system documentation is only injected into the AI context when relevant to the user's query.
*   **Immutable Infrastructure**: Standardized environment injection ensures the stack behaves identically in development and production.

---

## 📊 Google Ecosystem Integration
Fully optimized for the **Google Cloud Ecosystem**:
1.  **AI**: Gemini 1.5 Flash & Pro for semantic reasoning.
2.  **Persistence**: Google Sheets API as a live, collaborative security dashboard.
3.  **Security**: IAM Service Account authentication using encrypted environment injection.

---

## 🚦 Getting Started

### 1. Configuration
Create a `.env` file in the root directory:
```bash
GEMINI_API_KEY='your_key'
GOOGLE_SHEET_ID='your_sheet_id'
GOOGLE_SHEETS_CREDENTIALS='{"type": "service_account", ...}'
ADGUARD_USER='admin'
ADGUARD_PASS='your_password'
ADGUARD_URL='http://172.17.0.1:8080' # Docker Host Gateway
```

### 2. Deployment
```bash
docker compose down && docker compose up -d --build
```

---

## 🧪 Automated Verification
Reliability is proven, not promised. Run the **Full-Spectrum Test Suite** to verify mathematical and API integrity:

```bash
docker exec network-guardian pytest backend/tests/ -v
```
*Current Coverage: 100% Core Heuristic & API Failover Logic.*

---

## 👤 About the Architect
I am an engineer who thrives in high-stakes environments. My perspective is shaped by 30-hour incident responses, restoring 100% of data after catastrophic failures, and years of seeing the "inside" of the social media marketing machine. 

I don't just write code; I build guardians.

**"Isolation is the gift." — Charles Bukowski**

---

### License
MIT License - Open for the community to watch the watchers.
