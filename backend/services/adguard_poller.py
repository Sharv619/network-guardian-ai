import time
import requests
from datetime import datetime, timezone
from ..core.config import settings
from .gemini_analyzer import analyze_domain
# from .notion_service import push_threat # Removed: Pure Google Sheets mode
from .sheets_logger import log_threat_to_sheet
from ..logic.ml_heuristics import calculate_entropy, extract_domain_features, is_valid_domain
from ..logic.anomaly_engine import predict_anomaly
from ..core.state import automated_threats

# In-memory deduplication set
processed_domains = set()

def poll_adguard():
    print("Starting AdGuard Poller...")
    
    # SRE Pattern: Use persistent sessions for repeated polling
    session = requests.Session()
    session.auth = (settings.ADGUARD_USER, settings.ADGUARD_PASS)
    session.headers.update({"Accept": "application/json"})

    # Task 1: Harden the Poller URLs
    # Primary: http://adguard/control/querylog (Internal Port 80)
    # Secondary: http://172.17.0.1:8080/control/querylog (Host Gateway)
    target_urls = [
        "http://adguard/control/querylog",
        "http://172.17.0.1:8080/control/querylog"
    ]

    while True:
        try:
            success = False
            r = None
            for url in target_urls:
                try:
                    # Skip empty URLs if any
                    if "://" not in url: continue
                    
                    print(f"DEBUG: Polling AdGuard at {url}...")
                    r = session.get(url, timeout=5) # Reduced timeout for faster failover
                    
                    if r.status_code == 200:
                        success = True
                        print(f"DEBUG: AdGuard Status: {r.status_code}")
                        # If successful, process logs (logic below)
                        break 
                    elif r.status_code == 401:
                        print(f"CRITICAL: AdGuard Auth Failed at {url}. Check credentials.")
                        break # Auth fail means service is found but credentials wrong
                except requests.exceptions.RequestException:
                    continue # Try next URL
            
            if not success:
                print("AdGuard Poller: Could not connect to any AdGuard instance.")
                time.sleep(settings.POLL_INTERVAL)
                continue

            # Process valid response 'r' from the successful loop iteration
            # Task 1: Action: If the response is not JSON, log the first 100 characters
            content_type = r.headers.get('Content-Type', '')
            try:
                logs = r.json().get('data', [])
            except ValueError:
                print(f"AdGuard Response Error: Not JSON. Content-Type: {content_type}")
                print(f"Response starts with (Check for Install Wizard): {r.text[:100]}")
                time.sleep(settings.POLL_INTERVAL)
                continue

            # process logs
            for log in logs:
                domain = log.get('question', {}).get('name')
                
                # Validate domain to prevent terminal command leakage
                if not is_valid_domain(domain):
                    continue
                    
                if not domain or domain.endswith('.local') or domain.endswith('.arpa'):
                    continue

                if domain not in processed_domains:
                    print(f"Processing New Domain: {domain}")
                    
                    # --- Extract AdGuard Metadata ---
                    adguard_metadata = {
                        "reason": log.get("reason", "NotFilteredNotFound"),
                        "filter_id": log.get("filterId"),
                        "rule": log.get("rule"),
                        "client": log.get("client"),
                        "elapsed_ms": log.get("elapsedMs")
                    }
                    
                    # --- Local ML Heuristic Check ---
                    entropy = calculate_entropy(domain)
                    analysis = None
                    
                    # --- Anomaly Detection (Phase 2) ---
                    features = extract_domain_features(domain)
                    is_anomaly, anomaly_score = predict_anomaly(features)
                    
                    # Task 2: Automatic "Privacy Risk" Escalation
                    privacy_keywords = ['geo', 'location', 'gps', 'waa-pa', 'telemetry', 'analytics']
                    is_privacy_risk = any(kw in domain.lower() for kw in privacy_keywords)
                    
                    if is_privacy_risk:
                        print(f"PRIVACY RISK ESCALATION: {domain}")
                        try:
                            # Use specialized prompt for privacy risks
                            analysis = analyze_domain(
                                domain,
                                context={
                                    **adguard_metadata, 
                                    "privacy_audit": True
                                },
                                is_anomaly=is_anomaly,
                                anomaly_score=anomaly_score
                            )
                            analysis['timestamp'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                            analysis["is_anomaly"] = is_anomaly
                            analysis["anomaly_score"] = anomaly_score
                        except Exception as e:
                            print(f"Privacy Risk Analysis Failed: {e}")
                            # Fallback will handle it
                    
                    # Fallback to general tracker detection if not caught by privacy keywords
                    # (Though telemetry/analytics are in both lists now)
                    if analysis is None:
                         # Task 3: Background Tracker Priority (Legacy/General)
                        tracker_keywords = ['pixel', 'metrics', 'collect'] # Remaining keywords not in privacy list
                        is_tracker = any(kw in domain.lower() for kw in tracker_keywords)
                        
                        if is_tracker:
                            print(f"BACKGROUND TRACKER DETECTED: {domain}. Prioritizing analysis.")
                            try:
                                analysis = analyze_domain(
                                    domain,
                                    context={
                                        **adguard_metadata, 
                                        "tracker_alert": True
                                    },
                                    is_anomaly=is_anomaly,
                                    anomaly_score=anomaly_score
                                )
                                analysis['summary'] = "🚨 TELEMETRY INTERCEPTED: " + analysis['summary']
                                analysis['timestamp'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                                analysis["is_anomaly"] = is_anomaly
                                analysis["anomaly_score"] = anomaly_score
                            except Exception as e:
                                print(f"Tracker Analysis Failed: {e}")

                    if analysis is None:
                        if entropy > 3.8:
                            print(f"High Entropy Detected ({entropy:.2f}). Skipping Gemini.")
                            analysis = {
                                "risk_score": "High",
                                "category": "Malware",
                                "summary": f"High Entropy Domain ({entropy:.2f}). Likely DGA/C2.",
                                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                "is_anomaly": is_anomaly,
                                "anomaly_score": anomaly_score
                            }
                        else:
                            try:
                                print(f"Analyzing with Gemini: {domain} (Anomaly: {is_anomaly})")
                                # SRE Pattern: Pass AdGuard context to LLM for smarter analysis
                                analysis = analyze_domain(
                                    domain, 
                                    context=adguard_metadata,
                                    is_anomaly=is_anomaly,
                                    anomaly_score=anomaly_score
                                )
                                analysis['timestamp'] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                                analysis["is_anomaly"] = is_anomaly
                                analysis["anomaly_score"] = anomaly_score
                            except Exception as e:
                                print(f"Gemini API Failed: {e}. Falling back to Heuristics.")
                                analysis = {
                                    "risk_score": "Unknown",
                                    "category": "Unknown",
                                    "summary": f"Analysis failed. Entropy: {entropy:.2f}",
                                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                    "is_anomaly": is_anomaly,
                                    "anomaly_score": anomaly_score
                                }
                    
                    if is_anomaly and not adguard_metadata.get("filter_id"):
                        print(f"ZERO-DAY SUSPECT DETECTED: {domain}")
                        analysis = {
                            "risk_score": "High",
                            "category": "ZERO-DAY SUSPECT",
                            "summary": f"Unusual behavior detected by local ML (Score: {anomaly_score:.4f}). This domain bypassed traditional blocklists.",
                            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "is_anomaly": True,
                            "anomaly_score": anomaly_score
                        }

                    # Log to Persistence Layer (Pure Google Sheets)
                    # push_threat(domain, analysis) # Notion deprecated
                    log_threat_to_sheet(
                        domain, 
                        analysis, 
                        adguard_metadata=adguard_metadata,
                        is_anomaly=analysis.get("is_anomaly", False),
                        anomaly_score=analysis.get("anomaly_score", 0.0)
                    ) 
                    
                    # Task 3: Dashboard Real-Time Sync
                    # Update Live Memory (Automated Only)
                    automated_threats.insert(0, {
                        "domain": domain, 
                        "risk_score": analysis.get("risk_score"),
                        "category": analysis.get("category"),
                        "summary": analysis.get("summary"),
                        "timestamp": analysis.get("timestamp"),
                        "is_anomaly": analysis.get("is_anomaly", False),
                        "anomaly_score": analysis.get("anomaly_score", 0.0),
                        "adguard_metadata": adguard_metadata # Pass to frontend
                    })
                    # Keep buffer small
                    if len(automated_threats) > 50:
                        automated_threats.pop()
                    
                    processed_domains.add(domain)
                    if len(processed_domains) > 5000:
                        processed_domains.clear()
            
        except Exception as e:
            print(f"Poller Loop Error: {e}")
            
        time.sleep(settings.POLL_INTERVAL)
