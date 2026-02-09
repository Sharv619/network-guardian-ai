# Network Guardian AI: Project Antigravity

## Core Goals
Network Guardian AI is an automated threat intelligence pipeline that transforms network security monitoring from passive blocking to active, explainable AI-driven analysis. The project aims to provide:

1. **Real-time Threat Detection**: Monitor network traffic from AdGuard Home and analyze threats in real-time
2. **Explainable AI Analysis**: Use Google Gemini to provide human-readable explanations for security decisions
3. **Behavioral ML Integration**: Implement unsupervised learning models to detect anomalies and DGA (Domain Generation Algorithm) patterns
4. **Persistent Audit Trail**: Log all security decisions to Google Sheets for compliance and analysis
5. **Production-Ready Architecture**: Build with SRE principles including circuit breakers, graceful degradation, and observability

## What the App Does
Network Guardian AI intercepts DNS-level blocking data from AdGuard Home, applies multiple layers of analysis (Shannon Entropy heuristics, Isolation Forest ML model, and Google Gemini AI), and provides a comprehensive security dashboard. The system:

- **Intercepts**: Captures blocked domains from AdGuard Home's DNS filtering
- **Filters**: Applies local mathematical analysis to detect suspicious patterns
- **Learns**: Uses unsupervised ML to identify behavioral anomalies
- **Reasons**: Leverages Google Gemini to explain security decisions in human terms
- **Persists**: Streams verdicts to Google Sheets for permanent audit trails

## Key Features
- Live threat feed with real-time updates
- Manual domain analysis capability
- Hacker-style dark UI with status indicators
- Production-ready backend with circuit breakers
- Automated testing suite for reliability