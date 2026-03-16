"""
AdGuard Poller - Refactored to use DNS Adapter System
"""

import time
from datetime import UTC, datetime

from ..core.alerting import AlertSeverity, AlertType, alert_manager
from ..core.config import settings
from ..core.state import automated_threats
from ..core.utils import get_iso_timestamp
from ..logic.analysis_cache import cache_analysis_result, get_cached_analysis
from ..logic.anomaly_engine import predict_anomaly
from ..logic.knowledge_base import analyze_with_knowledge_base
from ..logic.metadata_classifier import (
    classifier,
    classify_domain_metadata,
    learn_from_completed_analysis,
)
from ..logic.ml_heuristics import (
    calculate_entropy,
    extract_domain_features,
    is_valid_domain,
    is_dga,
)
from ..logic.vector_store import vector_memory
from .gemini_analyzer import analyze_domain
from .sheets_logger import log_threat_to_sheet
from .dns_adapter.adguard import AdGuardAdapter

# In-memory deduplication set (kept for backward compatibility with existing code)
processed_domains = set()


def run_local_first_pipeline(
    domain: str,
    entropy: float,
    features: list,
    is_anomaly: bool,
    anomaly_score: float,
    adguard_metadata: dict,
) -> dict:
    """
    Local-first analysis pipeline for domain classification.
    This function is extracted for testability and follows the cascading logic:
    1. Metadata classification (if blocked by AdGuard)
    2. Entropy-based DGA detection
    3. Gemini AI fallback

    Returns analysis dict with risk_score, category, summary, and analysis_source.
    """
    from ..core.metrics import metrics_collector
    from ..logic.ml_heuristics import is_dga

    analysis = None

    # Stage 1: Metadata classification (for blocked domains)
    metadata_result = classify_domain_metadata(adguard_metadata)
    if metadata_result.confidence >= 0.8:
        classifier.increment_local_decision()
        analysis = {
            "risk_score": "High" if metadata_result.confidence > 0.9 else "Medium",
            "category": metadata_result.category,
            "summary": "🛡️ LOCAL ANALYSIS: Classified via metadata patterns",
            "timestamp": get_iso_timestamp(),
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "analysis_source": "metadata_classifier",
        }
        try:
            metrics_collector.record_classifier_decision("metadata")
        except Exception:
            pass
        return analysis

    # Stage 2: Entropy-based DGA detection
    if is_dga(domain) or entropy > 3.8:
        classifier.increment_local_decision()
        analysis = {
            "risk_score": "High",
            "category": "Malware",
            "summary": f"🛡️ LOCAL ANALYSIS: High Entropy ({entropy:.2f})",
            "timestamp": get_iso_timestamp(),
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "analysis_source": "entropy_heuristic",
        }
        try:
            metrics_collector.record_classifier_decision("entropy")
        except Exception:
            pass
        return analysis

    # Stage 3: Knowledge Base Analysis with API fallback (check mode setting)
    gemini_mode = getattr(settings, "GEMINI_MODE", "fallback")

    if gemini_mode == "always" or (gemini_mode == "fallback" and metadata_result.confidence < 0.8):
        try:
            print(f"Analyzing with Knowledge Base: {domain}")
            # Use knowledge base analysis which prioritizes local intelligence
            analysis = analyze_with_knowledge_base(
                domain, context=adguard_metadata, fallback_to_api=True
            )
            analysis["timestamp"] = get_iso_timestamp()
            analysis["is_anomaly"] = is_anomaly
            analysis["anomaly_score"] = anomaly_score

            # Update classifier decisions based on analysis source
            if analysis.get("analysis_source") == "gemini_api":
                classifier.increment_cloud_decision()
            else:
                classifier.increment_local_decision()

            try:
                metrics_collector.record_classifier_decision(
                    analysis.get("analysis_source", "knowledge_base")
                )
            except Exception:
                pass
            return analysis
        except Exception as e:
            print(f"Knowledge Base Analysis Failed for {domain}: {e}")
            import traceback

            traceback.print_exc()
            analysis = {
                "risk_score": "Unknown",
                "category": "Unknown",
                "summary": f"🛡️ LOCAL ANALYSIS: Analysis failed - {str(e)[:50]}",
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "is_anomaly": is_anomaly,
                "anomaly_score": anomaly_score,
                "analysis_source": "fallback_heuristic",
            }
            return analysis

    # Default fallback
    return {
        "risk_score": "Low",
        "category": "General Traffic",
        "summary": "🛡️ LOCAL ANALYSIS: No significant risk indicators",
        "timestamp": get_iso_timestamp(),
        "is_anomaly": is_anomaly,
        "anomaly_score": anomaly_score,
        "analysis_source": "local_heuristic",
    }


def poll_adguard():
    """
    Main polling function that uses the DNS Adapter system.
    This maintains backward compatibility while using the new adapter architecture.
    """
    print("Starting AdGuard Poller with DNS Adapter System...")

    # Create adapter instance
    adapter = AdGuardAdapter()

    # Test connection on startup
    success, message = adapter.test_connection()
    if not success:
        print(f"WARNING: {message}")
        # Continue anyway - might recover later

    last_poll_time = None

    while True:
        try:
            # Poll for new DNS queries
            dns_queries = adapter.poll_logs(since=last_poll_time)

            if dns_queries:
                print(f"Polled {len(dns_queries)} new DNS queries")
                last_poll_time = datetime.now(UTC)

            # Process each DNS query
            for dns_query in dns_queries:
                try:
                    # Skip if already processed (deduplication)
                    if dns_query.domain in processed_domains:
                        continue

                    print(f"Processing New Domain: {dns_query.domain}", flush=True)

                    # Convert DNSQuery to the adguard_metadata format expected by existing code
                    adguard_metadata = {
                        "reason": dns_query.reason or "NotFilteredNotFound",
                        "filter_id": dns_query.filter_id,
                        "rule": dns_query.rule or "",
                        "client": dns_query.client_ip,
                        "elapsed_ms": dns_query.elapsed_ms,
                    }

                    # Check cache
                    try:
                        cached_result = get_cached_analysis(dns_query.domain, adguard_metadata)
                    except Exception as e:
                        print(f"DEBUG: Cache error: {e}", flush=True)
                        cached_result = None

                    if cached_result:
                        print(f"Using cached analysis for {dns_query.domain}")
                        analysis = cached_result
                        analysis["timestamp"] = get_iso_timestamp()
                        # Get anomaly info from cached result if available
                        is_anomaly = analysis.get("is_anomaly", False)
                        anomaly_score = analysis.get("anomaly_score", 0.0)
                        # Calculate entropy for cache hit (needed for pipeline)
                        try:
                            entropy = calculate_entropy(dns_query.domain)
                        except:
                            entropy = 0.0
                        features = extract_domain_features(dns_query.domain)
                    else:
                        # Calculate entropy always
                        try:
                            entropy = calculate_entropy(dns_query.domain)
                        except:
                            entropy = 0.0

                        # Default values for anomaly detection
                        is_anomaly = False
                        anomaly_score = 0.0

                        features = extract_domain_features(dns_query.domain)
                        is_anomaly, anomaly_score = predict_anomaly(features)

                    # Use the local-first analysis pipeline
                    analysis = run_local_first_pipeline(
                        domain=dns_query.domain,
                        entropy=entropy,
                        features=features,
                        is_anomaly=is_anomaly,
                        anomaly_score=anomaly_score,
                        adguard_metadata=adguard_metadata,
                    )

                    # Handle the zero-day suspect case - this should create its own analysis
                    if (
                        is_anomaly
                        and not adguard_metadata.get("filter_id")
                        and anomaly_score < -0.1
                    ):
                        print(f"ZERO-DAY SUSPECT DETECTED: {dns_query.domain}")

                        # Trigger critical alert for zero-day suspect
                        import asyncio

                        try:
                            asyncio.create_task(
                                alert_manager.create_alert(
                                    alert_type=AlertType.ANOMALY_SPIKE,
                                    severity=AlertSeverity.CRITICAL,
                                    message=f"Zero-day suspect detected: {dns_query.domain} (anomaly_score: {anomaly_score:.4f})",
                                    details={
                                        "domain": dns_query.domain,
                                        "anomaly_score": anomaly_score,
                                        "is_anomaly": is_anomaly,
                                        "adguard_metadata": adguard_metadata,
                                        "analysis_source": "poller_zero_day_detection",
                                    },
                                )
                            )
                        except Exception as e:
                            print(f"Alert creation failed: {e}")

                        zero_day_analysis = {
                            "risk_score": "High",
                            "category": "ZERO-DAY SUSPECT",
                            "summary": f"Unusual ML score: {anomaly_score:.4f}",
                            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                            "is_anomaly": True,
                            "anomaly_score": anomaly_score,
                        }
                        # Use the zero-day analysis instead of the previous one
                        analysis = zero_day_analysis

                    # Safety check: ensure analysis is always defined before using it
                    if analysis is None:
                        print(
                            f"WARNING: No analysis could be generated for {dns_query.domain}, using fallback"
                        )
                        analysis = {
                            "risk_score": "Unknown",
                            "category": "Unknown",
                            "summary": "🛡️ LOCAL ANALYSIS: No analysis could be generated",
                            "timestamp": get_iso_timestamp(),
                            "is_anomaly": is_anomaly,
                            "anomaly_score": anomaly_score,
                            "analysis_source": "fallback",
                        }

                    log_threat_to_sheet(
                        dns_query.domain,
                        analysis,
                        adguard_metadata=adguard_metadata or {},
                        is_anomaly=analysis.get("is_anomaly", False),
                        anomaly_score=analysis.get("anomaly_score", 0.0),
                        entropy=entropy,
                    )

                    automated_threats.insert(
                        0,
                        {
                            "domain": dns_query.domain,
                            "risk_score": analysis.get("risk_score"),
                            "category": analysis.get("category"),
                            "summary": analysis.get("summary"),
                            "timestamp": analysis.get("timestamp"),
                            "is_anomaly": analysis.get("is_anomaly", False),
                            "anomaly_score": analysis.get("anomaly_score", 0.0),
                            "adguard_metadata": adguard_metadata,
                        },
                    )

                    if len(automated_threats) > 50:
                        automated_threats.pop()

                    if analysis and analysis.get("analysis_source") != "cached":
                        cache_ttl = 1800 if analysis.get("analysis_source") == "gemini_ai" else 3600
                        cache_analysis_result(
                            dns_query.domain,
                            adguard_metadata,
                            analysis,
                            analysis.get("analysis_source", "unknown"),
                            cache_ttl,
                        )

                        category = analysis.get("category")
                        if (
                            analysis.get("analysis_source") == "gemini_ai"
                            and category
                            and category not in ["Unknown", "General Traffic"]
                        ):
                            learn_from_completed_analysis(
                                dns_query.domain, adguard_metadata, category
                            )

                    similar_threats = vector_memory.query_memory(dns_query.domain, k=3)
                    has_similarity_match = len(similar_threats) > 0

                    metadata = {
                        "domain": dns_query.domain,
                        "summary": analysis.get("summary", ""),
                        "category": analysis.get("category", ""),
                        "risk_score": analysis.get("risk_score", ""),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    vector_memory.add_to_memory(dns_query.domain, metadata)

                    # Notify threat callbacks (used by WebSocket manager)
                    try:
                        from ..core.state import notify_threat_detected

                        threat_data = {
                            "domain": dns_query.domain,
                            "risk_score": analysis.get("risk_score", "Unknown"),
                            "category": analysis.get("category", "Unknown"),
                            "summary": analysis.get("summary", "Awaiting audit..."),
                            "timestamp": analysis.get(
                                "timestamp",
                                datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                            ),
                            "is_anomaly": analysis.get("is_anomaly", False),
                            "anomaly_score": analysis.get("anomaly_score", 0.0),
                            "adguard_metadata": adguard_metadata,
                            "analysis_source": analysis.get("analysis_source", "unknown"),
                            "entropy": entropy,
                            "has_similarity_match": has_similarity_match,
                        }
                        notify_threat_detected(threat_data)
                    except Exception as ws_error:
                        print(f"Threat notification error: {ws_error}", flush=True)

                    processed_domains.add(dns_query.domain)
                    if len(processed_domains) > 5000:
                        processed_domains.clear()

                except Exception as e:
                    import traceback as tb

                    tb_str = tb.format_exc()
                    print("=== DOMAIN PROCESSING ERROR ===", flush=True)
                    print(f"Error: {e}", flush=True)
                    print(f"Traceback:\n{tb_str}", flush=True)
                    print("=== END ERROR ===", flush=True)

        except Exception as e:
            import traceback as tb

            tb_str = tb.format_exc()
            print("##########################################", flush=True)
            print("# POLLER ERROR AT TOP LEVEL - REBUILD OK #", flush=True)
            print("##########################################", flush=True)
            print(f"Poller Loop Error: {e}", flush=True)
            print(f"Traceback:\n{tb_str}", flush=True)
            print("##########################################", flush=True)

        time.sleep(settings.POLL_INTERVAL)
