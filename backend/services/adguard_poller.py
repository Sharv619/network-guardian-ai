"""
AdGuard Poller - Refactored to use DNS Adapter System
"""

import time
from collections import deque
from datetime import UTC, datetime

from ..core.alerting import AlertSeverity, AlertType, alert_manager
from ..core.config import settings
from ..core.state import append_threat, get_threat_count, pop_threat
from ..core.utils import get_iso_timestamp
from ..logic.analysis_cache import cache_analysis_result, get_cached_analysis
from ..logic.anomaly_engine import predict_anomaly
from ..logic.metadata_classifier import (
    classifier,
    classify_domain_metadata,
    learn_from_completed_analysis,
)
from ..logic.ml_heuristics import (
    calculate_entropy,
    extract_domain_features,
    is_dga,
)
from ..services.ollama_analyzer import analyze_with_ollama
from ..logic.vector_store import vector_memory
from .dns_adapter.adguard import AdGuardAdapter
from .sheets_logger import log_threat_to_sheet

# In-memory deduplication with bounded size (LRU eviction via deque)
processed_domains: deque[str] = deque(maxlen=5000)


def save_domain_to_repository(
    tenant_id: int,
    domain: str,
    analysis: dict,
    entropy: float,
    features: list,
    adguard_metadata: dict | None = None,
) -> None:
    """Save domain analysis to SQLAlchemy repository for multi-tenant persistence.

    This bridges the gap between the old synchronous poller and the new async repository.
    """
    try:
        import asyncio
        from datetime import UTC, datetime

        from ..db.database import get_session
        from ..db.repository import DomainRepository

        async def _save():
            async with get_session() as session:
                repo = DomainRepository(session, tenant_id=tenant_id)

                analysis_result = {
                    "domain": domain,
                    "entropy": entropy,
                    "risk_score": analysis.get("risk_score", "Unknown"),
                    "category": analysis.get("category", "Unknown"),
                    "summary": analysis.get("summary"),
                    "is_anomaly": analysis.get("is_anomaly", False),
                    "anomaly_score": analysis.get("anomaly_score", 0.0),
                    "analysis_source": analysis.get("analysis_source", "adguard_poller"),
                    "timestamp": analysis.get("timestamp") or datetime.now(UTC).isoformat(),
                    "adguard_metadata": adguard_metadata,
                    "features": {
                        "length": len(domain),
                        "digit_ratio": sum(c.isdigit() for c in domain) / max(len(domain), 1),
                        "vowel_ratio": sum(c.lower() in "aeiou" for c in domain)
                        / max(len(domain), 1),
                        "non_alphanumeric": sum(not c.isalnum() for c in domain),
                    }
                    if features
                    else None,
                }

                await repo.create_domain_from_analysis(analysis_result)
                await session.commit()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_save())
        except RuntimeError:
            # No running loop — poller thread has no event loop.
            # Create a temporary one to run the save.
            asyncio.run(_save())
    except Exception as e:
        print(f"Warning: Could not save domain to repository: {e}")


def _get_adguard_whitelist() -> set:
    """Fetch whitelist from AdGuard's allowed domains via API."""
    try:
        import requests
        from ..core.config import settings

        if not settings.ADGUARD_URL:
            return set()

        # Try to fetch from AdGuard's safebrowsing API or filtering status
        base_url = settings.ADGUARD_URL.replace("/control/querylog", "")
        if "/control" in base_url:
            base_url = base_url.split("/control")[0]

        # Try filtering status endpoint
        resp = requests.get(
            f"{base_url}/control/filtering/status",
            auth=(settings.ADGUARD_USER, settings.ADGUARD_PASS),
            timeout=5,
        )

        if resp.status_code == 200:
            data = resp.json()
            whitelist = set()

            # Check whitelist_filters
            if data.get("whitelist_filters"):
                for wf in data["whitelist_filters"]:
                    if wf.get("url"):
                        # Would need to fetch the filter list - skip for now
                        pass

            # Check user_rules
            if data.get("user_rules"):
                for rule in data["user_rules"]:
                    if rule and isinstance(rule, str):
                        # Extract domain from rule like "@@||example.com^"
                        if rule.startswith("@@||"):
                            domain = rule.replace("@@||", "").replace("^", "").replace("|", "")
                            if domain:
                                whitelist.add(domain)

            if whitelist:
                print(f"Loaded {len(whitelist)} domains from AdGuard allowlist")
                return whitelist
    except Exception as e:
        print(f"Could not fetch AdGuard whitelist: {e}")

    return set()


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
    LOCAL HEURISTICS ARE THE CORE - Gemini enhances for unique per-domain insights.

    1. Metadata classification (uses adguard_metadata from DNS adapter)
    2. Entropy-based DGA detection
    3. Shannon Entropy + Anomaly analysis
    4. Gemini AI enhancement (OPTIONAL - if enabled)
    """
    from ..core.config import settings
    from ..core.metrics import metrics_collector

    # Stage 1: Metadata classification (ONLY for blocked domains)
    # Only use metadata classification when AdGuard actually filtered/blocked the domain
    # For domains that passed through normally, skip to entropy/local analysis
    reason = adguard_metadata.get("reason", "")
    filter_id = adguard_metadata.get("filter_id")
    is_blocked = filter_id is not None or (reason and reason.startswith("Filtered"))

    if is_blocked:
        metadata_result = classify_domain_metadata(adguard_metadata)
        if metadata_result.confidence >= 0.8:
            classifier.increment_local_decision()
            try:
                metrics_collector.record_classifier_decision("metadata")
            except Exception:
                pass
            return {
                "risk_score": "High" if metadata_result.confidence > 0.9 else "Medium",
                "category": metadata_result.category,
                "summary": f"🛡️ SOC GUARD ACTIVE: Local heuristic audit completed. Metadata pattern matched ({metadata_result.category})",
                "timestamp": get_iso_timestamp(),
                "is_anomaly": is_anomaly,
                "anomaly_score": anomaly_score,
                "analysis_source": "metadata_classifier",
            }

    # Stage 2: Entropy-based DGA detection (HIGH priority)
    if is_dga(domain) or entropy > 3.8:
        classifier.increment_local_decision()
        try:
            metrics_collector.record_classifier_decision("entropy")
        except Exception:
            pass
        return {
            "risk_score": "High",
            "category": "Malware",
            "summary": f"🛡️ SOC GUARD ACTIVE: Local heuristic audit completed. Risk verified via Shannon Entropy ({entropy:.2f}). DGA pattern detected.",
            "timestamp": get_iso_timestamp(),
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "analysis_source": "entropy_heuristic",
        }

    # Stage 3: LOCAL ANALYSIS with Shannon Entropy + Anomaly Detection
    # This is THE CORE FEATURE - always run locally
    classifier.increment_local_decision()
    try:
        metrics_collector.record_classifier_decision("local_heuristic")
    except Exception:
        pass

    # Build comprehensive local analysis
    entropy_level = "LOW" if entropy < 2.5 else "MEDIUM" if entropy < 3.5 else "HIGH"

    # Known-safe domains that should never reach Ollama
    # CDNs, major services, and common subdomains with naturally high entropy
    safe_tlds = (
        "googlevideo.com",
        "googleapis.com",
        "gstatic.com",
        "fastly.net",
        "fastly-edge.com",
        "cloudfront.net",
        "akamai.net",
        "azureedge.net",
    )
    domain_lower = domain.lower()
    is_known_safe = any(domain_lower.endswith(tld) for tld in safe_tlds)

    if is_known_safe:
        risk_score = "Low"
        category = "General Traffic"
        summary = f"🛡️ SOC GUARD ACTIVE: Known-safe CDN/service domain. Entropy ({entropy:.2f}, {entropy_level}) is normal for this infrastructure."
    elif anomaly_score > 0.5:
        risk_score = "High"
        category = "Suspicious Activity"
        summary = f"🛡️ SOC GUARD ACTIVE: Local heuristic audit completed. Risk verified via Shannon Entropy ({entropy:.2f}, {entropy_level}). Anomaly score: {anomaly_score:.4f} - Potential threat pattern detected."
    elif entropy > 3.5:
        risk_score = "Medium"
        category = "Suspicious Activity"
        summary = f"🛡️ SOC GUARD ACTIVE: Local heuristic audit completed. Risk verified via Shannon Entropy ({entropy:.2f}, {entropy_level}). Elevated entropy detected."
    else:
        risk_score = "Low"
        category = "General Traffic"
        summary = f"🛡️ SOC GUARD ACTIVE: Local heuristic audit completed. Risk verified via Shannon Entropy ({entropy:.2f}, {entropy_level}). Normal network behavior patterns consistent with legitimate traffic."

    local_analysis = {
        "risk_score": risk_score,
        "category": category,
        "summary": summary,
        "timestamp": get_iso_timestamp(),
        "is_anomaly": is_anomaly,
        "anomaly_score": anomaly_score,
        "entropy_score": entropy,
        "analysis_source": "local_heuristic",
    }

    # STAGE 4: OLLAMA AI ENHANCEMENT
    # Call Ollama ONLY for Medium/High risk to get unique per-domain insights
    # Falls back to local heuristics if Ollama is unavailable (e.g., insufficient RAM)
    if settings.OLLAMA_LIVE_FEED_ENABLED and risk_score in ["Medium", "High"]:
        try:
            ollama_context = {
                "reason": adguard_metadata.get("reason", ""),
                "rule": adguard_metadata.get("rule", ""),
                "local_entropy": entropy,
                "local_anomaly": anomaly_score,
            }

            ollama_analysis = analyze_with_ollama(
                domain,
                context=ollama_context,
                model=settings.OLLAMA_CHAT_MODEL,
            )

            if ollama_analysis and ollama_analysis.get("risk_score"):
                # Only use Ollama result if it's not the fallback heuristic
                source = ollama_analysis.get("analysis_source", "")
                if "fallback" not in source:
                    local_analysis["summary"] = ollama_analysis.get(
                        "summary", local_analysis["summary"]
                    )
                    local_analysis["analysis_source"] = "ollama_ai_enhanced"
                    local_analysis["confidence"] = ollama_analysis.get("confidence", 0.8)
                    print(
                        f"[OLLAMA ENHANCEMENT] ✅ Enhanced {domain}: {ollama_analysis.get('category')}"
                    )
                    time.sleep(settings.OLLAMA_CALL_COOLDOWN)
        except Exception as e:
            print(f"[OLLAMA ENHANCEMENT] Fallback to local analysis: {e}")
            pass

    return local_analysis


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
                            alert_manager.create_alert_sync(
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

                    # Save to SQLAlchemy repository for multi-tenant persistence
                    save_domain_to_repository(
                        tenant_id=1,  # Default tenant for backward compatibility
                        domain=dns_query.domain,
                        analysis=analysis,
                        entropy=entropy,
                        features=features,
                        adguard_metadata=adguard_metadata,
                    )

                    append_threat(
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

                    # Update real-time trend data
                    from backend.core.state import update_trend_count

                    risk = analysis.get("risk_score", "").lower()
                    is_threat = risk in ["high", "medium"]
                    is_anomaly = analysis.get("is_anomaly", False)
                    is_safe = risk == "low"
                    update_trend_count(is_threat=is_threat, is_anomaly=is_anomaly, is_safe=is_safe)

                    if analysis and analysis.get("analysis_source") != "cached":
                        cache_ttl = (
                            1800
                            if analysis.get("analysis_source") == "ollama_ai_enhanced"
                            else 3600
                        )
                        cache_analysis_result(
                            dns_query.domain,
                            adguard_metadata,
                            analysis,
                            analysis.get("analysis_source", "unknown"),
                            cache_ttl,
                        )

                        category = analysis.get("category")
                        if category and category not in ["Unknown", "General Traffic"]:
                            # Learn from any analysis source (Gemini or local)
                            source = analysis.get("analysis_source", "unknown")
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

                    processed_domains.append(dns_query.domain)

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
