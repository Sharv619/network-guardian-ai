# Network Guardian AI - Sample Data Examples

## Live System Data Examples

### Example 1: Google Video Domain Analysis
```json
{
  "domain": "rr8---sn-v2u0n-hxad.googlevideo.com",
  "risk_score": "High",
  "category": "System/Tracker",
  "summary": "YouTube video streaming domain - legitimate but tracks viewing behavior",
  "timestamp": "2026-10-02T09:08:15Z",
  "is_anomaly": false,
  "anomaly_score": 0.0537,
  "adguard_metadata": {
    "reason": "NotFilteredNotFound",
    "rule": null
  },
  "entropy": 2.85,
  "analysis_source": "AI Analysis Only"
}
```

### Example 2: High Entropy DGA Domain
```json
{
  "domain": "xhk92-z1.ru",
  "risk_score": "Critical",
  "category": "Malware",
  "summary": "Domain Generation Algorithm (DGA) pattern detected - likely malware C2 communication",
  "timestamp": "2026-10-02T09:15:32Z",
  "is_anomaly": true,
  "anomaly_score": -0.15,
  "adguard_metadata": {
    "reason": "Blocked by rule",
    "rule": "||xhk92-z1.ru^"
  },
  "entropy": 4.2,
  "analysis_source": "Entropy Analysis + AI"
}
```

### Example 3: Privacy Violation Detection
```json
{
  "domain": "geo-location-tracker.example.com",
  "risk_score": "High",
  "category": "Privacy Violation",
  "summary": "Geolocation tracking domain attempting to collect user location data",
  "timestamp": "2026-10-02T09:22:18Z",
  "is_anomaly": true,
  "anomaly_score": -0.08,
  "adguard_metadata": {
    "reason": "Blocked by privacy filter",
    "rule": "||geo-location-tracker.example.com^"
  },
  "entropy": 3.1,
  "analysis_source": "Pattern Recognition + AI"
}
```

## Google Sheets Integration Data

### Sheet Structure (Columns A-J)
| A (Timestamp) | B (Domain) | C (Risk Score) | D (Category) | E (Summary) | F (AdGuard Reason) | G (AdGuard Rule) | H (Is Anomaly) | I (Anomaly Score) | J (Entropy) |
|---------------|------------|----------------|--------------|-------------|-------------------|------------------|----------------|-------------------|-------------|
| 2026-10-02T09:08:15Z | rr8---sn-v2u0n-hxad.googlevideo.com | High | System/Tracker | YouTube video streaming domain - legitimate but tracks viewing behavior | NotFilteredNotFound | | FALSE | 0.0537 | 2.85 |
| 2026-10-02T09:15:32Z | xhk92-z1.ru | Critical | Malware | Domain Generation Algorithm (DGA) pattern detected - likely malware C2 communication | Blocked by rule | \|\|xhk92-z1.ru^ | TRUE | -0.15 | 4.2 |
| 2026-10-02T09:22:18Z | geo-location-tracker.example.com | High | Privacy Violation | Geolocation tracking domain attempting to collect user location data | Blocked by privacy filter | \|\|geo-location-tracker.example.com^ | TRUE | -0.08 | 3.1 |

## System Intelligence Dashboard Data

### Real-time Metrics
```json
{
  "autonomy_score": 78,
  "local_decisions": 156,
  "cloud_decisions": 44,
  "total_decisions": 200,
  "patterns_learned": 1234,
  "seed_patterns": 850,
  "learned_patterns": 384,
  "classifier": {
    "total_patterns": 1234,
    "category_distribution": {
      "Tracker": 450,
      "Advertising": 320,
      "Malware": 180,
      "System": 150,
      "Privacy": 134
    }
  },
  "cache": {
    "memory_cache_size": 5000,
    "valid_memory_entries": 4850,
    "disk_cache_exists": true,
    "cache_file_size": 245760
  }
}
```

## Analysis Pipeline Examples

### Tier 1: Cache Hit (Fastest - <10ms)
```
Domain: google.com
Cache Result: HIT
Risk Score: Low
Category: System
Source: Cached from previous analysis
```

### Tier 2: Metadata Classification (Local - ~50ms)
```
Domain: ads.trackingnetwork.com
Metadata Match: "ads" keyword detected
Risk Score: Medium
Category: Advertising
Source: Local pattern matching
```

### Tier 3: ML Heuristics (Local - ~100ms)
```
Domain: x9k2m5n8.ru
Entropy Score: 4.1
Digit Ratio: 0.4
Risk Score: High
Category: Malware
Source: Shannon Entropy + Digit Analysis
```

### Tier 4: Anomaly Detection (Local - ~200ms)
```
Domain: unusual-pattern.example.net
Isolation Forest Score: -0.12
Anomaly Detected: TRUE
Risk Score: High
Category: Unknown
Source: Behavioral anomaly detection
```

### Tier 5: Gemini AI Analysis (Cloud - ~2s)
```
Domain: complex-suspicious-domain.com
AI Analysis: Full semantic analysis
Risk Score: Critical
Category: Malware
Summary: "This domain exhibits characteristics of a sophisticated malware command & control server..."
Source: Google Gemini AI
```

## Manual Analysis Example

### User Input
```
Domain: suspicious-download-site.com
Registrar: Unknown
Age: 2 days
```

### System Response
```json
{
  "domain": "suspicious-download-site.com",
  "risk_score": "Critical",
  "category": "Malware",
  "summary": "Newly registered domain with high entropy (4.3) hosting malicious downloads. Pattern matches known malware distribution network.",
  "timestamp": "2026-10-02T09:30:45Z",
  "entropy_score": 4.3,
  "anomaly_score": -0.18,
  "semantic_match_found": true,
  "pattern_match": "High Entropy Domain",
  "analysis_source": "Entropy Analysis + AI"
}
```

## Threat Detection Patterns

### Privacy Violation Keywords
- `geo`, `location`, `gps`, `telemetry`, `waa-pa`
- Auto-escalated to Gemini AI for detailed analysis

### Tracker Pattern Detection
- `pixel`, `metrics`, `collect`, `analytics`
- Auto-flagged as tracking domains

### Malware Indicators
- Entropy > 3.8
- Newly registered domains (< 30 days)
- Numeric-heavy domains (digit ratio > 0.3)

## Performance Metrics

### Response Times
- Cache Hit: < 10ms
- Local Heuristics: 50-200ms
- AI Analysis: 1-3s
- Average Response: 400ms

### Cost Optimization
- 78% of domains handled locally (no AI cost)
- 22% escalated to Gemini AI
- Cache hit rate: 70-80%
- Monthly AI API cost reduction: ~85%

## System Status Indicators

### Health Status
- **HEALTHY**: Autonomy Score > 50% and Total Decisions > 0
- **WARMING UP**: Total Decisions = 0 (system starting)
- **NEEDS ATTENTION**: Autonomy Score < 50% (too many AI calls)

### Live Feed Filters
- **HIGH RISK ONLY**: Shows only domains with "High" or "Critical" risk scores
- **ALL THREATS**: Shows all analyzed domains regardless of risk level

This sample data demonstrates how Network Guardian AI processes, analyzes, and logs network threats in real-time while maintaining cost efficiency through intelligent local processing.