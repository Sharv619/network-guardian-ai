import time
import traceback
import sys
import requests
from datetime import datetime, timezone
from ..core.utils import get_iso_timestamp
from ..core.config import settings
from .gemini_analyzer import analyze_domain
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
                    r = session.get(url, timeout=5)
                    
                    if r.status_code == 200:
                        success = True
                        print(f"DEBUG: AdGuard Status: {r.status_code}")
                        break 
                    elif r.status_code == 401:
                        print(f"CRITICAL: AdGuard Auth Failed at {url}. Check credentials.")
                        break
                except requests.exceptions.RequestException:
                    continue
            
            if not success:
                print("AdGuard Poller: Could not connect to any AdGuard instance.")
                time.sleep(settings.POLL_INTERVAL)
                continue

            if r is None:
                print("AdGuard Response Error: No response received")
                time.sleep(settings.POLL_INTERVAL)
                continue
                
            content_type = r.headers.get('Content-Type', '')
            try:
                logs = r.json().get('data', [])
            except ValueError:
                print(f"AdGuard Response Error: Not JSON. Content-Type: {content_type}")
                print(f"Response starts with: {r.text[:100]}")
                time.sleep(settings.POLL_INTERVAL)
                continue

            # process logs
            for log in logs:
                try:
                    if log is None or 'question' not in log:
                        continue
                        
                    question = log.get('question')
                    if question is None:
                        continue
                        
                    domain_data = question.get('name')
                    if not domain_data:
                        continue
                        
                    domain = str(domain_data).lower().strip()
                    
                    if not is_valid_domain(domain):
                        continue
                        
                    if not domain or domain.endswith('.local') or domain.endswith('.arpa'):
                        continue

                    if domain not in processed_domains:
                        print(f"Processing New Domain: {domain}", flush=True)
                        
                        adguard_metadata = {
                            "reason": log.get("reason", "NotFilteredNotFound"),
                            "filter_id": log.get("filterId"),
                            "rule": log.get("rule") or "",
                            "client": log.get("client") or "",
                            "elapsed_ms": log.get("elapsedMs")
                        }
                        
                        # Check cache
                        try:
                            cached_result = get_cached_analysis(domain, adguard_metadata)
                        except Exception as e:
                            print(f"DEBUG: Cache error: {e}", flush=True)
                            cached_result = None
                            
                        # Calculate entropy always
                        try:
                            entropy = calculate_entropy(domain)
                        except:
                            entropy = 0.0
                        
                        # Default values for anomaly detection
                        is_anomaly = False
                        anomaly_score = 0.0
                        
                        if cached_result:
                            print(f"Using cached analysis for {domain}")
                            analysis = cached_result
                            analysis['timestamp'] = get_iso_timestamp()
                            # Get anomaly info from cached result if available
                            is_anomaly = analysis.get("is_anomaly", False)
                            anomaly_score = analysis.get("anomaly_score", 0.0)
                        else:
                            features = extract_domain_features(domain)
                            is_anomaly, anomaly_score = predict_anomaly(features)
                        
                        # Privacy check
                        privacy_keywords = ['geo', 'location', 'gps', 'waa-pa', 'telemetry', 'analytics']
                        try:
                            is_privacy_risk = any(kw in domain.lower() for kw in privacy_keywords)
                        except Exception as e:
                            print(f"DEBUG: Privacy check error: {e}", flush=True)
                            is_privacy_risk = False
                        
                        if is_privacy_risk:
                            print(f"PRIVACY RISK ESCALATION: {domain}")
                            try:
                                analysis = analyze_domain(
                                    domain,
                                    context={**adguard_metadata, "privacy_audit": True},
                                    is_anomaly=is_anomaly,
                                    anomaly_score=anomaly_score
                                )
                                analysis['timestamp'] = get_iso_timestamp()
                                analysis["is_anomaly"] = is_anomaly
                                analysis["anomaly_score"] = anomaly_score
                            except Exception as e:
                                print(f"Privacy Risk Analysis Failed: {e}")

                        if analysis is None:
                            tracker_keywords = ['pixel', 'metrics', 'collect']
                            is_tracker = any(kw in domain.lower() for kw in tracker_keywords)
                            
                            if is_tracker:
                                print(f"BACKGROUND TRACKER DETECTED: {domain}")
                                try:
                                    analysis = analyze_domain(
                                        domain,
                                        context={**adguard_metadata, "tracker_alert": True},
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
                            metadata_result = classify_domain_metadata(adguard_metadata)
                            if metadata_result.confidence >= 0.8:
                                print(f"METADATA CLASSIFICATION: {domain} -> {metadata_result.category}")
                                classifier.increment_local_decision()
                                analysis = {
                                    "risk_score": "High" if metadata_result.confidence > 0.9 else "Medium",
                                    "category": metadata_result.category,
                                    "summary": f"🛡️ LOCAL ANALYSIS: Classified via metadata patterns",
                                    "timestamp": get_iso_timestamp(),
                                    "is_anomaly": is_anomaly,
                                    "anomaly_score": anomaly_score,
                                    "analysis_source": "metadata_classifier"
                                }
                            elif entropy > 3.8:
                                print(f"High Entropy Detected ({entropy:.2f})")
                                analysis = {
                                    "risk_score": "High",
                                    "category": "Malware",
                                    "summary": f"🛡️ LOCAL ANALYSIS: High Entropy ({entropy:.2f})",
                                    "timestamp": get_iso_timestamp(),
                                    "is_anomaly": is_anomaly,
                                    "anomaly_score": anomaly_score,
                                    "analysis_source": "entropy_heuristic"
                                }
                            else:
                                try:
                                    print(f"Analyzing with Gemini: {domain}")
                                    classifier.increment_cloud_decision()
                                    analysis = analyze_domain(domain, context=adguard_metadata, is_anomaly=is_anomaly, anomaly_score=anomaly_score)
                                    analysis['timestamp'] = get_iso_timestamp()
                                    analysis["is_anomaly"] = is_anomaly
                                    analysis["anomaly_score"] = anomaly_score
                                    analysis["analysis_source"] = "gemini_ai"
                                except Exception as e:
                                    print(f"Gemini API Failed: {e}")
                                    analysis = {
                                        "risk_score": "Unknown",
                                        "category": "Unknown",
                                        "summary": f"🛡️ LOCAL ANALYSIS: Analysis failed",
                                        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                        "is_anomaly": is_anomaly,
                                        "anomaly_score": anomaly_score,
                                        "analysis_source": "fallback_heuristic"
                                    }
                        
                        if is_anomaly and not adguard_metadata.get("filter_id") and anomaly_score < -0.1:
                            print(f"ZERO-DAY SUSPECT DETECTED: {domain}")
                            analysis = {
                                "risk_score": "High",
                                "category": "ZERO-DAY SUSPECT",
                                "summary": f"Unusual ML score: {anomaly_score:.4f}",
                                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                "is_anomaly": True,
                                "anomaly_score": anomaly_score
                            }

                        log_threat_to_sheet(
                            domain, 
                            analysis, 
                            adguard_metadata=adguard_metadata or {},
                            is_anomaly=analysis.get("is_anomaly", False),
                            anomaly_score=analysis.get("anomaly_score", 0.0)
                        )
                        
                        automated_threats.insert(0, {
                            "domain": domain, 
                            "risk_score": analysis.get("risk_score"),
                            "category": analysis.get("category"),
                            "summary": analysis.get("summary"),
                            "timestamp": analysis.get("timestamp"),
                            "is_anomaly": analysis.get("is_anomaly", False),
                            "anomaly_score": analysis.get("anomaly_score", 0.0),
                            "adguard_metadata": adguard_metadata
                        })
                        
                        if len(automated_threats) > 50:
                            automated_threats.pop()
                        
                        if analysis and analysis.get("analysis_source") != "cached":
                            cache_ttl = 1800 if analysis.get("analysis_source") == "gemini_ai" else 3600
                            cache_analysis_result(domain, adguard_metadata, analysis, analysis.get("analysis_source", "unknown"), cache_ttl)
                            
                            category = analysis.get("category")
                            if analysis.get("analysis_source") == "gemini_ai" and category and category not in ["Unknown", "General Traffic"]:
                                learn_from_completed_analysis(domain, adguard_metadata, category)
                        
                        similar_threats = vector_memory.query_memory(domain, k=3)
                        has_similarity_match = len(similar_threats) > 0
                        
                        metadata = {
                            "domain": domain,
                            "summary": analysis.get("summary", ""),
                            "category": analysis.get("category", ""),
                            "risk_score": analysis.get("risk_score", ""),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        vector_memory.add_to_memory(domain, metadata)
                        
                        threat_entry = {
                            "domain": domain, 
                            "risk_score": analysis.get("risk_score", "Unknown"),
                            "category": analysis.get("category", "Unknown"),
                            "summary": analysis.get("summary", "Awaiting audit..."),
                            "timestamp": analysis.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
                            "is_anomaly": analysis.get("is_anomaly", False),
                            "anomaly_score": analysis.get("anomaly_score", 0.0),
                            "adguard_metadata": adguard_metadata,
                            "analysis_source": analysis.get("analysis_source", "unknown"),
                            "entropy": entropy if 'entropy' in dir() else 0.0,
                            "has_similarity_match": has_similarity_match
                        }
                        
                        processed_domains.add(domain)
                        if len(processed_domains) > 5000:
                            processed_domains.clear()
                except Exception as e:
                    import traceback as tb
                    tb_str = tb.format_exc()
                    print(f"=== DOMAIN PROCESSING ERROR ===", flush=True)
                    print(f"Error: {e}", flush=True)
                    print(f"Traceback:\n{tb_str}", flush=True)
                    print(f"=== END ERROR ===", flush=True)
            
        except Exception as e:
            import traceback as tb
            tb_str = tb.format_exc()
            print(f"##########################################", flush=True)
            print(f"# POLLER ERROR AT TOP LEVEL - REBUILD OK #", flush=True)
            print(f"##########################################", flush=True)
            print(f"Poller Loop Error: {e}", flush=True)
            print(f"Traceback:\n{tb_str}", flush=True)
            print(f"##########################################", flush=True)
        
        time.sleep(settings.POLL_INTERVAL)
