# Network Guardian AI - Architecture Documentation

A comprehensive guide to the system architecture, evolution phases, and technical implementation.

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Phase 1: Foundation](#phase-1-foundation-days-1-4)
3. [Phase 2: Core Logic](#phase-2-core-logic-days-5-11)
4. [Phase 3: Optimization](#phase-3-optimization-days-12-16)
5. [Complete Architecture](#complete-architecture)
6. [File Structure](#file-structure)
7. [Data Flow](#data-flow)
8. [Performance Metrics](#performance-metrics)

---

## System Overview

Network Guardian AI is an automated threat intelligence pipeline that transforms network security monitoring from passive blocking to active, explainable AI-driven analysis.

### Core Capabilities
- **Real-time Threat Detection**: Monitor DNS traffic and analyze threats in real-time
- **Multi-layered Analysis**: Shannon Entropy → Isolation Forest → Gemini AI
- **Explainable AI**: Human-readable explanations for security decisions
- **Persistent Audit Trail**: Google Sheets integration for compliance
- **80% Test Coverage**: Production-ready reliability

---

## Phase 1: Foundation (Days 1-4)

### Evolution Timeline

```mermaid
graph LR
    subgraph "Phase 1: Foundation"
        D1[Day 1<br/>Vision] --> D2[Day 2<br/>Docker]
        D2 --> D3[Day 3<br/>FastAPI]
        D3 --> D4[Day 4<br/>Security]
    end
    
    style D1 fill:#e1f5fe
    style D2 fill:#e8f5e9
    style D3 fill:#fff3e0
    style D4 fill:#fce4ec
```

### Day 1: Problem Definition

```mermaid
mindmap
  root((Problem))
    Network Visibility Gap
      Consumers blind to DNS traffic
      No insight into background requests
      Telemetry goes unnoticed
    Solution Requirements
      Real-time threat detection
      20+ historical records
      Human-readable intelligence
      Multi-layered analysis
```

### Day 2: Docker Infrastructure

```mermaid
graph TB
    subgraph "Docker Compose Architecture"
        DC[docker-compose.yml]
        
        subgraph "Services"
            NG[Network Guardian<br/>Port 8000]
            AG[AdGuard Home<br/>Port 53, 3000]
        end
        
        subgraph "Volumes"
            VW[adguard_work]
            VC[adguard_conf]
        end
        
        subgraph "Network"
            NET[network-guardian-net<br/>Bridge Driver]
        end
        
        DC --> NG
        DC --> AG
        AG --> VW
        AG --> VC
        NG --> NET
        AG --> NET
    end
    
    subgraph "Health Checks"
        HC1[HTTP :8000/health]
        HC2[Wget :80/spider]
    end
    
    NG -.-> HC1
    AG -.-> HC2
    
    style NG fill:#4caf50,color:#fff
    style AG fill:#2196f3,color:#fff
```

### Day 3: FastAPI Backend

```mermaid
graph TB
    subgraph "FastAPI Application Structure"
        MAIN[main.py<br/>App Entry Point]
        
        subgraph "Core Features"
            ASYNC[Async Processing]
            BG[Background Tasks]
            OD[OpenAPI Docs /docs]
        end
        
        subgraph "Endpoints"
            HEALTH[/health]
            ANALYZE[/analyze]
            CHAT[/chat]
            HISTORY[/history]
            STATS[/api/stats/system]
        end
        
        MAIN --> ASYNC
        MAIN --> BG
        MAIN --> OD
        MAIN --> HEALTH
        MAIN --> ANALYZE
        MAIN --> CHAT
        MAIN --> HISTORY
        MAIN --> STATS
    end
    
    style MAIN fill:#009688,color:#fff
    style ASYNC fill:#00bcd4,color:#fff
    style BG fill:#00bcd4,color:#fff
```

### Day 4: Security Patterns

```mermaid
graph TB
    subgraph "Defense in Depth - Security Layer"
        subgraph "Layer 1: Input"
            VAL[Input Validation]
            SAN[Sanitization]
        end
        
        subgraph "Layer 2: Rate Limiting"
            RL[Rate Limiter<br/>100 req/min]
            IP[IP Tracking]
        end
        
        subgraph "Layer 3: Resilience"
            CB[Circuit Breaker]
            FALL[Fallback Logic]
        end
        
        subgraph "Layer 4: Auth"
            JWT[JWT Authentication]
            API[API Keys]
        end
        
        VAL --> SAN --> RL --> IP --> CB --> FALL
        JWT --> API
    end
    
    style CB fill:#f44336,color:#fff
    style FALL fill:#ff9800,color:#fff
```

---

## Phase 2: Core Logic (Days 5-11)

### Evolution Timeline

```mermaid
graph LR
    subgraph "Phase 2: Core Logic"
        D5[Day 5<br/>React UI] --> D6[Day 6<br/>Sheets]
        D6 --> D7[Day 7<br/>AdGuard]
        D7 --> D8[Day 8<br/>Defense]
        D8 --> D9[Day 9<br/>Entropy]
        D9 --> D10[Day 10<br/>ML]
        D10 --> D11[Day 11<br/>Gemini]
    end
    
    style D9 fill:#9c27b0,color:#fff
    style D10 fill:#673ab7,color:#fff
    style D11 fill:#3f51b5,color:#fff
```

### Three-Stage Analysis Pipeline

```mermaid
flowchart TB
    START[DNS Query Intercepted] --> CACHE{Cache<br/>Hit?}
    
    CACHE -->|Yes| RESP[Return Cached<br/>Analysis]
    CACHE -->|No| ENT{Stage 1<br/>Shannon Entropy<br/>~0.0001s}
    
    ENT -->|High Entropy<br/>> 3.8| FLAG1[🚨 Flag as DGA<br/>Domain Generation Algorithm]
    ENT -->|Normal| ML{Stage 2<br/>Isolation Forest<br/>~0.001s}
    
    ML -->|Anomaly Detected| FLAG2[⚠️ Flag as Anomaly]
    ML -->|Normal Behavior| AI{Stage 3<br/>Gemini AI<br/>~1.2s}
    
    AI --> VERDICT[📋 Final Verdict<br/>+ Human Explanation]
    
    FLAG1 --> LOG[Google Sheets<br/>Audit Log]
    FLAG2 --> LOG
    VERDICT --> LOG
    
    LOG --> UI[React Dashboard<br/>Real-time Update]
    
    style ENT fill:#9c27b0,color:#fff
    style ML fill:#673ab7,color:#fff
    style AI fill:#3f51b5,color:#fff
    style FLAG1 fill:#f44336,color:#fff
    style FLAG2 fill:#ff9800,color:#fff
```

### Day 9: Shannon Entropy Implementation

```mermaid
flowchart LR
    subgraph "Entropy Calculation"
        DOMAIN[Domain Name] --> CLEAN[Preprocess<br/>Remove TLD]
        CLEAN --> COUNT[Character<br/>Frequency Count]
        COUNT --> CALC[H = -Σ p·log₂p]
        CALC --> SCORE[Entropy Score]
    end
    
    subgraph "DGA Detection"
        SCORE --> THRESH{Score > 3.8?}
        THRESH -->|Yes| DGA[🚨 DGA Detected]
        THRESH -->|No| PASS[✓ Pass to ML]
    end
    
    subgraph "Performance"
        P1[10,000 domains/sec]
        P2[92% Detection Rate]
        P3[Sub-millisecond]
    end
    
    style CALC fill:#9c27b0,color:#fff
    style DGA fill:#f44336,color:#fff
```

### Day 10: Isolation Forest ML

```mermaid
flowchart TB
    subgraph "Feature Extraction"
        F1[Domain Length]
        F2[Subdomain Count]
        F3[Uppercase Count]
        F4[Lowercase Count]
        F5[Digit Count]
        F6[Special Chars]
        F7[Entropy Score]
        F8[Vowel Ratio]
        F9[Consonant Ratio]
        F10[Digit Ratio]
        F11[Special Char Ratio]
        F12[Repeated Chars]
    end
    
    subgraph "ML Model"
        FE[Feature Vector<br/>12 dimensions]
        IF[Isolation Forest<br/>contamination=0.05]
        SCORE[Anomaly Score]
    end
    
    F1 & F2 & F3 & F4 & F5 & F6 & F7 & F8 & F9 & F10 & F11 & F12 --> FE
    FE --> IF --> SCORE
    
    subgraph "Results"
        SCORE --> DEC{Score < -0.1?}
        DEC -->|Yes| ANOM[⚠️ Anomaly]
        DEC -->|No| NORMAL[✓ Normal]
    end
    
    style IF fill:#673ab7,color:#fff
```

### Day 11: Google Gemini Integration

```mermaid
sequenceDiagram
    participant DP as Domain Pipeline
    participant GA as Gemini Analyzer
    participant GEM as Gemini 2.0 Flash
    participant FB as Fallback
    
    DP->>GA: analyze_domain(domain, context)
    GA->>GA: Build Prompt with Context
    GA->>GEM: generate_content(prompt)
    
    alt Success
        GEM-->>GA: Structured JSON Response
        GA->>GA: Parse & Validate
        GA-->>DP: ThreatVerdict
    else Rate Limited (429)
        GEM-->>GA: 429 Error
        GA->>GA: Retry with Backoff
        GA->>FB: Try Fallback Models
        FB-->>DP: Fallback Response
    else API Error
        GEM-->>GA: Error
        GA->>GA: Heuristic Fallback
        GA-->>DP: Local Analysis Result
    end
    
    Note over GA,FB: 90% Cost Savings via<br/>Local Pre-filtering
```

---

## Phase 3: Optimization (Days 12-16)

### Evolution Timeline

```mermaid
graph LR
    subgraph "Phase 3: Optimization"
        D12[Day 12<br/>Caching] --> D13[Day 13<br/>Pipeline]
        D13 --> D14[Day 14<br/>Errors]
        D14 --> D15[Day 15<br/>Docker Opt]
        D15 --> D16[Day 16<br/>UI Polish]
    end
    
    style D12 fill:#00bcd4,color:#fff
    style D13 fill:#009688,color:#fff
    style D14 fill:#4caf50,color:#fff
```

### Caching Strategy

```mermaid
flowchart TB
    subgraph "Multi-Level Cache"
        L1[L1: Memory Cache<br/>Instant Access]
        L2[L2: Disk Cache<br/>JSON Persistence]
        L3[L3: Google Sheets<br/>Permanent Record]
    end
    
    subgraph "Cache Flow"
        REQ[Analysis Request] --> CHECK{L1 Hit?}
        CHECK -->|Yes| RET1[Return Instant]
        CHECK -->|No| CHECK2{L2 Hit?}
        CHECK2 -->|Yes| LOAD[Load from Disk]
        CHECK2 -->|No| PIPE[Run Full Pipeline]
        LOAD --> RET2[Return Fast]
        PIPE --> STORE[Store L1 + L2]
        STORE --> RET3[Return Result]
    end
    
    style L1 fill:#4caf50,color:#fff
    style L2 fill:#ff9800,color:#fff
    style L3 fill:#2196f3,color:#fff
```

### Real-Time Pipeline Architecture

```mermaid
flowchart TB
    subgraph "Producer"
        ADG[AdGuard Home]
        POLL[30s Poller]
    end
    
    subgraph "Queue Management"
        QUEUE[Async Queue<br/>Max 1000 items]
        SEM[Semaphore<br/>Max 10 concurrent]
    end
    
    subgraph "Consumer"
        WORKER[Worker Pool]
        ANALYZE[Analysis Pipeline]
    end
    
    subgraph "Output"
        CACHE[Cache Update]
        SHEETS[Google Sheets]
        WS[WebSocket Broadcast]
    end
    
    ADG --> POLL --> QUEUE --> SEM --> WORKER --> ANALYZE
    ANALYZE --> CACHE
    ANALYZE --> SHEETS
    ANALYZE --> WS
    
    style QUEUE fill:#ff5722,color:#fff
    style SEM fill:#795548,color:#fff
```

### Error Handling & Resilience

```mermaid
flowchart TB
    subgraph "Error Handling Layers"
        subgraph "Layer 1: Retry"
            R1[Attempt 1]
            R2[Attempt 2<br/>+1s delay]
            R3[Attempt 3<br/>+5s delay]
        end
        
        subgraph "Layer 2: Fallback"
            F1[Gemini 2.0 Flash]
            F2[Gemini 1.5 Pro]
            F3[Local Heuristics]
        end
        
        subgraph "Layer 3: Circuit Breaker"
            CB[Open Circuit<br/>after 5 failures]
            HALF[Half-Open<br/>after 30s]
            CLOSE[Close Circuit<br/>on success]
        end
    end
    
    R1 -->|Fail| R2 -->|Fail| R3
    R3 -->|Fail| F1 -->|Fail| F2 -->|Fail| F3
    F1 & F2 -->|5 failures| CB --> HALF --> CLOSE
    
    style CB fill:#f44336,color:#fff
    style F3 fill:#4caf50,color:#fff
```

---

## Complete Architecture

### Full System Diagram

```mermaid
graph TB
    subgraph "External Services"
        GEMINI[Google Gemini API]
        SHEETS[Google Sheets]
        ADGUARD[AdGuard Home<br/>DNS Server]
    end
    
    subgraph "Network Guardian AI Container"
        subgraph "Frontend :3000"
            REACT[React Dashboard]
            WSCLIENT[WebSocket Client]
        end
        
        subgraph "Backend :8000"
            FASTAPI[FastAPI Server]
            
            subgraph "Core Services"
                POLLER[DNS Poller<br/>30s interval]
                WEBSOCKET[WebSocket Manager]
            end
            
            subgraph "Analysis Pipeline"
                CACHE{Cache Check}
                ENTROPY[Shannon Entropy<br/>~0.0001s]
                IFOREST[Isolation Forest<br/>~0.001s]
                GEMINI_SVC[Gemini Analyzer<br/>~1.2s]
                FALLBACK[Heuristic Fallback]
            end
            
            subgraph "Storage"
                MEMORY[In-Memory State]
                SQLITE[SQLite Database]
                DISK_CACHE[Disk Cache JSON]
            end
        end
    end
    
    ADGUARD -->|Query Logs| POLLER
    POLLER --> CACHE
    CACHE -->|Miss| ENTROPY
    ENTROPY --> IFOREST
    IFOREST --> GEMINI_SVC
    GEMINI_SVC -->|API Error| FALLBACK
    GEMINI_SVC --> SHEETS
    FALLBACK --> SHEETS
    GEMINI_SVC --> MEMORY
    FALLBACK --> MEMORY
    MEMORY --> WEBSOCKET
    WEBSOCKET --> WSCLIENT
    WSCLIENT --> REACT
    MEMORY --> SQLITE
    CACHE --> DISK_CACHE
    GEMINI_SVC -.->|AI Analysis| GEMINI
    
    style GEMINI_SVC fill:#3f51b5,color:#fff
    style ENTROPY fill:#9c27b0,color:#fff
    style IFOREST fill:#673ab7,color:#fff
```

---

## File Structure

```
network-guardian-ai/
│
├── 📁 backend/
│   ├── 📄 __init__.py
│   ├── 📄 main.py                    # FastAPI app entry point
│   ├── 📄 requirements.txt           # Python dependencies
│   │
│   ├── 📁 api/                       # API Routes
│   │   ├── 📄 router.py              # Main API endpoints
│   │   ├── 📄 auth_router.py         # Authentication routes
│   │   ├── 📄 alert_router.py        # Alert management
│   │   ├── 📄 stats.py               # System statistics
│   │   └── 📄 ws_router.py           # WebSocket routes
│   │
│   ├── 📁 core/                      # Core Configuration
│   │   ├── 📄 config.py              # Settings (Pydantic)
│   │   ├── 📄 auth.py                # JWT & API Key management
│   │   ├── 📄 middleware.py          # Request middleware
│   │   ├── 📄 rate_limiter.py        # Rate limiting logic
│   │   ├── 📄 validators.py          # Input validation
│   │   └── 📄 alerting.py            # Alert system
│   │
│   ├── 📁 logic/                     # Analysis Logic
│   │   ├── 📄 ml_heuristics.py       # Shannon Entropy ⚡
│   │   ├── 📄 anomaly_engine.py      # Isolation Forest 🤖
│   │   ├── 📄 metadata_classifier.py # Pattern classification
│   │   ├── 📄 vector_store.py        # Memory store
│   │   ├── 📄 analysis_cache.py      # Caching layer
│   │   └── 📄 feature_engineering.py # Feature extraction
│   │
│   ├── 📁 services/                  # External Integrations
│   │   ├── 📄 adguard_poller.py      # DNS query polling
│   │   ├── 📄 gemini_analyzer.py     # Gemini AI integration 🧠
│   │   ├── 📄 sheets_logger.py       # Google Sheets logging
│   │   └── 📄 db_logger.py           # Database logging
│   │
│   ├── 📁 db/                        # Database Layer
│   │   ├── 📄 database.py            # SQLAlchemy setup
│   │   ├── 📄 models.py              # ORM models
│   │   ├── 📄 repository.py          # Data access
│   │   └── 📄 backup.py              # Backup utilities
│   │
│   └── 📁 tests/                     # Test Suite (80% coverage)
│       ├── 📄 test_heuristics.py     # Entropy tests
│       ├── 📄 test_anomaly_engine.py # ML tests
│       ├── 📄 test_gemini_integration.py # AI tests
│       └── 📄 test_*.py              # Other tests
│
├── 📁 frontend/
│   ├── 📄 App.tsx                    # Main React component
│   ├── 📄 index.tsx                  # Entry point
│   ├── 📄 types.ts                   # TypeScript types
│   │
│   ├── 📁 components/
│   │   ├── 📄 Dashboard.tsx          # Main dashboard
│   │   ├── 📄 SystemIntelligence.tsx # Live metrics
│   │   ├── 📄 ThreatAnalysisPanel.tsx
│   │   └── 📄 ChatPanel.tsx
│   │
│   └── 📁 services/
│       └── 📄 geminiService.ts       # API client
│
├── 📁 docs/
│   ├── 📄 ARCHITECTURE.md            # This file
│   └── 📄 AUTHENTICATION.md          # Auth docs
│
├── 📁 linkedin_posts/                # Development journey
│   └── 📄 day_*.md                   # 16-day series
│
├── 📄 docker-compose.yml             # Container orchestration
├── 📄 Dockerfile                     # Multi-stage build
├── 📄 README.md                      # Project overview
├── 📄 AGENTS.md                      # Development guidelines
└── 📄 .env.example                   # Environment template
```

---

## Data Flow

### Request Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Cache
    participant Entropy
    participant ML
    participant Gemini
    participant Sheets
    
    Client->>FastAPI: GET /history
    FastAPI->>Cache: Check cache
    Cache-->>FastAPI: Return cached data
    FastAPI-->>Client: JSON response
    
    Note over Client,Sheets: New domain analysis
    
    Client->>FastAPI: POST /analyze {domain}
    FastAPI->>Cache: Check cache
    Cache-->>FastAPI: Cache miss
    
    FastAPI->>Entropy: Calculate entropy
    Entropy-->>FastAPI: Score: 4.2 (High)
    
    alt High entropy
        FastAPI->>FastAPI: Flag as suspicious
    else Normal entropy
        FastAPI->>ML: Anomaly detection
        ML-->>FastAPI: Score: -0.15
        
        alt Anomaly detected
            FastAPI->>FastAPI: Flag as anomaly
        else Normal
            FastAPI->>Gemini: AI analysis
            Gemini-->>FastAPI: ThreatVerdict
        end
    end
    
    FastAPI->>Sheets: Log result
    FastAPI->>Cache: Store result
    FastAPI-->>Client: Analysis result
```

---

## Performance Metrics

### System Performance

| Metric | Value | Description |
|--------|-------|-------------|
