import time
import requests
from datetime import datetime, timezone
from ..core.utils import get_iso_timestamp
from ..core.config import settings
from .gemini_analyzer import analyze_domain
# from .notion_service import push_threat # Removed: Pure Google Sheets mode
from .sheets_logger import log_threat_to_sheet
from ..logic.ml_heuristics import calculate_entropy, extract_domain_features, is_valid_domain
from ..logic.anomaly_engine import predict_anomaly
from ..logic.metadata_classifier import classify_domain_metadata, learn_from_completed_analysis, classifier
from ..logic.analysis_cache import get_cached_analysis, cache_analysis_result
from ..core.state import automated_threats
from ..logic.vector_store import vector_memory

# In-memory deduplication set
processed_domains = set()

def poll_adguard():
    print("Starting AdGuard Poller...")
    
    # SRE Pattern: Use persistent sessions for repeated polling
    session = requests.Session()
    if settings.ADGUARD_USER and settings.ADGUARD_PASS:
        session.auth = (settings.ADGUARD_USER, settings.ADGUARD_PASS)
    session.headers.update({"Accept": "application/json"})

    # Task 1: Harden the Poller URLs
    # Use configured AdGuard URL first, then fallbacks
    target_urls = []
    
    # Add configured URL if available
    if settings.ADGUARD_URL:
        configured_url = f"{settings.ADGUARD_URL}/control/querylog"
        target_urls.append(configured_url)
    
    # Add fallback URLs
    target_urls.extend([
        "http://172.17.0.1:8080/control/querylog",
        "http://adguard:80/control/querylog"
    ])

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
            if r is None:
                print("AdGuard Response Error: No response received")
                time.sleep(settings.POLL_INTERVAL)
                continue
                
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
                # CRITICAL: Add null safety check to prevent 'NoneType' error
                if log is None or 'question' not in log:
                    continue
                    
                # Enhanced null safety for domain extraction
                question = log.get('question', {})
                if not question or 'name' not in question:
                    continue
                    
                domain_data = question.get('name', '')
                if not domain_data:
                    continue
                    
                domain = str(domain_data).lower().strip()
                
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
                    
                    # --- Smart Routing: Check Cache First ---
                    cached_result = get_cached_analysis(domain, adguard_metadata)
                    if cached_result:
                        print(f"Using cached analysis for {domain}")
                        analysis = cached_result
                        # Update timestamp for cache freshness
                        analysis['timestamp'] = get_iso_timestamp()
                    else:
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
                            analysis['timestamp'] = get_iso_timestamp()
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
                                analysis['timestamp'] = get_iso_timestamp()
                                analysis["is_anomaly"] = is_anomaly
                                analysis["anomaly_score"] = anomaly_score
                            except Exception as e:
                                print(f"Tracker Analysis Failed: {e}")

                    if analysis is None:
                        # --- Smart Routing: Try Metadata Classification First ---
                        metadata_result = classify_domain_metadata(adguard_metadata)
                        if metadata_result.confidence >= 0.8:
                            print(f"METADATA CLASSIFICATION: {domain} -> {metadata_result.category} (Confidence: {metadata_result.confidence:.2f})")
                            # Track local decision
                            classifier.increment_local_decision()
                            analysis = {
                                "risk_score": "High" if metadata_result.confidence > 0.9 else "Medium",
                                "category": metadata_result.category,
                                "summary": f"🛡️ LOCAL ANALYSIS: Classified via AdGuard metadata patterns. Source: {metadata_result.source}",
                                "timestamp": get_iso_timestamp(),
                                "is_anomaly": is_anomaly,
                                "anomaly_score": anomaly_score,
                                "analysis_source": "metadata_classifier"
                            }
                        elif entropy > 3.8:
                            print(f"High Entropy Detected ({entropy:.2f}). Skipping Gemini.")
                            analysis = {
                                "risk_score": "High",
                                "category": "Malware",
                                "summary": f"🛡️ LOCAL ANALYSIS: High Entropy Domain ({entropy:.2f}). Likely DGA/C2.",
                                "timestamp": get_iso_timestamp(),
                                "is_anomaly": is_anomaly,
                                "anomaly_score": anomaly_score,
                                "analysis_source": "entropy_heuristic"
                            }
                        else:
                            try:
                                print(f"Analyzing with Gemini: {domain} (Anomaly: {is_anomaly})")
                                # Track cloud decision
                                classifier.increment_cloud_decision()
                                # SRE Pattern: Pass AdGuard context to LLM for smarter analysis
                                analysis = analyze_domain(
                                    domain, 
                                    context=adguard_metadata,
                                    is_anomaly=is_anomaly,
                                    anomaly_score=anomaly_score
                                )
                                analysis['timestamp'] = get_iso_timestamp()
                                analysis["is_anomaly"] = is_anomaly
                                analysis["anomaly_score"] = anomaly_score
                                analysis["analysis_source"] = "gemini_ai"
                            except Exception as e:
                                print(f"Gemini API Failed: {e}. Falling back to Heuristics.")
                                analysis = {
                                    "risk_score": "Unknown",
                                    "category": "Unknown",
                                    "summary": f"🛡️ LOCAL ANALYSIS: Analysis failed. Entropy: {entropy:.2f}",
                                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                    "is_anomaly": is_anomaly,
                                    "anomaly_score": anomaly_score,
                                    "analysis_source": "fallback_heuristic"
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
                        adguard_metadata=adguard_metadata or {},
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
                    
                    # --- Cache and Learn ---
                    if analysis and analysis.get("analysis_source") != "cached":
                        # Cache the result for future use
                        cache_ttl = 1800 if analysis.get("analysis_source") == "gemini_ai" else 3600  # 30 min for Gemini, 1 hour for local
                        cache_analysis_result(domain, adguard_metadata, analysis, analysis.get("analysis_source", "unknown"), cache_ttl)
                        
                        # Learn from the analysis to improve metadata patterns
                        category = analysis.get("category")
                        if analysis.get("analysis_source") == "gemini_ai" and category and category not in ["Unknown", "General Traffic"]:
                            learn_from_completed_analysis(domain, adguard_metadata, category)
                    
                    # Check for semantic similarity using vector memory
                    similar_threats = vector_memory.query_memory(domain, k=3)
                    has_similarity_match = len(similar_threats) > 0
                    
                    # Add to vector memory for future reference
                    metadata = {
                        "domain": domain,
                        "summary": analysis.get("summary", ""),
                        "category": analysis.get("category", ""),
                        "risk_score": analysis.get("risk_score", ""),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    vector_memory.add_to_memory(domain, metadata)
                    
                    # Ensure all required fields are present for frontend
                    threat_entry = {
                        "domain": domain, 
                        "risk_score": analysis.get("risk_score", "Unknown"),
                        "category": analysis.get("category", "Unknown"),
                        "summary": analysis.get("summary", "Awaiting heuristic audit..."),
                        "timestamp": analysis.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
                        "is_anomaly": analysis.get("is_anomaly", False),
                        "anomaly_score": analysis.get("anomaly_score", 0.0),
                        "adguard_metadata": adguard_metadata,
                        "has_similarity_match": has_similarity_match
                    }
                    
                    processed_domains.add(domain)
                    if len(processed_domains) > 5000:
                        processed_domains.clear()
            
        except Exception as e:
            print(f"Poller Loop Error: {e}")
            
        time.sleep(settings.POLL_INTERVAL)
