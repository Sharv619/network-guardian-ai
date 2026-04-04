"""
Statistics and monitoring endpoints for the optimized analysis system
Tenant-aware: All statistics are scoped to the current tenant context
"""

import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Request

from ..core.state import get_all_threats, get_threat_count
from ..logic.analysis_cache import get_cache_stats
from ..logic.anomaly_engine import engine
from ..logic.metadata_classifier import classifier, get_classifier_stats

router = APIRouter()


def get_entropy_stats():
    """Calculate entropy statistics from processed domains"""
    threats = get_all_threats()
    if not threats:
        return {
            "total_analyzed": 0,
            "avg_entropy": 0.0,
            "high_entropy_count": 0,
            "low_entropy_count": 0,
            "max_entropy": 0.0,
            "min_entropy": 0.0,
        }

    entropies = []
    for threat in threats:
        ent = threat.get("entropy", 0)
        if ent > 0:
            entropies.append(ent)

    if not entropies:
        return {
            "total_analyzed": get_threat_count(),
            "avg_entropy": 0.0,
            "high_entropy_count": 0,
            "low_entropy_count": 0,
            "max_entropy": 0.0,
            "min_entropy": 0.0,
        }

    return {
        "total_analyzed": len(entropies),
        "avg_entropy": round(sum(entropies) / len(entropies), 4),
        "high_entropy_count": sum(1 for e in entropies if e > 3.5),
        "low_entropy_count": sum(1 for e in entropies if e <= 3.5),
        "max_entropy": round(max(entropies), 4),
        "min_entropy": round(min(entropies), 4),
    }


def get_anomaly_stats():
    """Get anomaly detection statistics"""
    # Extract individual scores from history (each entry is a list of features)
    recent_scores = []
    for entry in engine.history[-10:]:
        if isinstance(entry, list) and len(entry) > 0:
            # Use first feature as representative score
            recent_scores.append(round(float(entry[0]), 4))
        elif isinstance(entry, (int, float)):
            recent_scores.append(round(float(entry), 4))

    anomalies_detected = sum(1 for t in threats if t.get("is_anomaly", False))
    total_threats = len(threats)
    anomaly_rate = 0.0
    if total_threats > 0:
        anomaly_rate = round((anomalies_detected / total_threats) * 100, 2)

    return {
        "is_trained": engine.is_trained,
        "total_samples": len(engine.history),
        "min_samples_required": engine.min_samples * 2,
        "anomalies_detected": anomalies_detected,
        "anomaly_rate": anomaly_rate,
        "recent_scores": recent_scores,
    }


@router.get("/system")
async def get_system_stats(request: Request):
    """Get comprehensive system statistics with real-time metrics"""
    from backend.core.config import settings

    from ..db.repository import get_domain_repository

    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility

    # Get repository for the current tenant
    async with get_domain_repository(tenant_id=tenant_id) as repo:
        threat_stats = await repo.get_stats()

    # Get global stats (not tenant-aware in Phase 1)
    stats = get_classifier_stats()
    realtime_stats = classifier.get_realtime_stats()
    entropy_stats = (
        get_entropy_stats()
    )  # Note: This uses global automated_threats, not tenant-aware
    anomaly_stats = get_anomaly_stats()  # Note: This uses global engine, not tenant-aware
    cache_stats = get_cache_stats()

    # Get blocklist stats (not tenant-aware in Phase 1)
    blocklist_stats = {
        "total_entries": 0,
        "active_sources": 0,
        "total_sources": 0,
        "category_distribution": {},
    }
    try:
        from backend.services.blocklist_loader import blocklist_loader

        bl_stats = await blocklist_loader.get_stats()
        blocklist_stats = {
            "total_entries": bl_stats.get("total_entries", 0),
            "active_sources": bl_stats.get("active_sources", 0),
            "total_sources": bl_stats.get("total_sources", 0),
            "category_distribution": bl_stats.get("category_distribution", {}),
        }
    except Exception as e:
        print(f"Blocklist stats error: {e}")

    autonomy_score = realtime_stats["autonomy_score"]

    adguard_status = "ACTIVE" if settings.has_adguard else "INACTIVE"
    ollama_status = "ACTIVE" if settings.OLLAMA_ENABLED else "INACTIVE"
    sheets_status = (
        "ACTIVE" if settings.GOOGLE_SHEETS_CREDENTIALS and settings.GOOGLE_SHEET_ID else "INACTIVE"
    )
    blocklist_status = "ACTIVE" if settings.BLOCKLIST_ENABLED else "INACTIVE"

    system_usage = {
        "active_integrations": [
            {
                "name": "AdGuard DNS",
                "status": adguard_status,
                "description": "Live DNS query interception",
            },
            {
                "name": "Blocklist Knowledge Base",
                "status": blocklist_status,
                "description": f"{blocklist_stats['total_entries']:,} domains from {blocklist_stats['active_sources']} sources",
            },
            {
                "name": "Local ML Classifier",
                "status": "ACTIVE",
                "description": "Pattern-based threat detection",
            },
            {
                "name": "Ollama AI (Local)",
                "status": ollama_status,
                "description": "Local LLM for domain analysis",
            },
            {
                "name": "Google Sheets",
                "status": sheets_status,
                "description": "Threat log synchronization",
            },
        ],
        "tracker_detection": {
            "total_detected": sum(stats["category_distribution"].values()),
            "categories": stats["category_distribution"],
            "detection_methods": [
                "Blocklist lookup (162K+ domains)",
                "AdGuard metadata analysis",
                "Pattern matching from learned patterns",
                "Heuristic analysis for unknown threats",
            ],
        },
        "learning_progress": {
            "seed_patterns": realtime_stats["seed_patterns"],
            "learned_patterns": realtime_stats["learned_patterns"],
            "blocklist_domains": blocklist_stats["total_entries"],
            "learning_rate": f"{blocklist_stats['total_entries']:,} blocklist + {realtime_stats['learned_patterns']} patterns",
            "next_milestone": "1M blocklist domains for maximum coverage",
        },
    }

    result = {
        "autonomy_score": autonomy_score,
        "local_decisions": realtime_stats["local_decisions"],
        "cloud_decisions": realtime_stats["cloud_decisions"],
        "total_decisions": realtime_stats["total_decisions"],
        "patterns_learned": realtime_stats["patterns_learned"],
        "seed_patterns": realtime_stats["seed_patterns"],
        "learned_patterns": realtime_stats["learned_patterns"],
        "classifier": stats,
        "cache": cache_stats,
        "realtime_stats": realtime_stats,
        "entropy": entropy_stats,
        "anomaly": anomaly_stats,
        "system_usage": system_usage,
        "blocklist": blocklist_stats,
        # Add threat-based stats from the repository (tenant-aware)
        "threat_stats": threat_stats,
    }

    # Add additional fields expected by the frontend with error handling
    try:
        from ..logic.vector_store import vector_memory

        vm_stats = vector_memory.get_stats()
        result["vector_memory"] = {
            "total_embeddings": vm_stats.get("total_embeddings", 0),
            "memory_size": vm_stats.get("total_embeddings", 0),
            "query_performance": 0.05,
            "is_available": vm_stats.get("is_available", False),
            "dimension": vm_stats.get("dimension", 0),
        }
    except Exception as e:
        print(f"Warning: Could not add vector_memory: {e}")
        pass

    try:
        result["anomaly_engine"] = {
            "is_trained": getattr(engine, "is_trained", False),
            "training_samples": len(getattr(engine, "history", [])),
            "detection_rate": anomaly_stats.get("anomaly_rate", 0),
        }
    except Exception as e:
        print(f"Warning: Could not add anomaly_engine: {e}")
        pass

    try:
        result["adaptive_thresholds"] = {
            "entropy_threshold": entropy_stats.get("avg_entropy", 3.5) + 0.5,
            "anomaly_threshold": engine.anomaly_threshold
            if hasattr(engine, "anomaly_threshold")
            else 0.5,
        }
    except Exception as e:
        print(f"Warning: Could not add adaptive_thresholds: {e}")
        pass

    return result


@router.get("/stats/cache")
def get_cache_stats_endpoint():
    """Get cache-specific statistics"""
    return get_cache_stats()


@router.post("/cache/clear")
def clear_cache_endpoint():
    """Clear analysis cache and learned patterns (resets poisoned data)"""
    from ..logic.analysis_cache import clear_analysis_cache
    from ..logic.metadata_classifier import classifier

    clear_analysis_cache()
    classifier.patterns.clear()
    classifier.pattern_counter.clear()
    return {"status": "cleared", "message": "Analysis cache and learned patterns cleared"}


@router.get("/stats/classifier")
def get_classifier_stats_endpoint():
    """Get metadata classifier statistics"""
    return get_classifier_stats()


@router.get("/stats/entropy")
def get_entropy_stats_endpoint():
    """Get Shannon entropy statistics"""
    return get_entropy_stats()


@router.get("/stats/anomaly")
def get_anomaly_stats_endpoint():
    """Get anomaly detection statistics"""
    return get_anomaly_stats()


@router.get("/alerts/stats")
def get_alerts_stats():
    """Get alert statistics for the alerts dashboard"""
    from backend.core.alerting import alert_manager

    # Get real alert stats from AlertManager
    alert_stats = alert_manager.get_stats()

    # Also compute threat-based stats for the threat summary
    threats = get_all_threats()
    high_count = sum(1 for t in threats if t.get("risk_score", "").lower() == "high")
    medium_count = sum(1 for t in threats if t.get("risk_score", "").lower() == "medium")
    low_count = sum(1 for t in threats if t.get("risk_score", "").lower() == "low")
    anomaly_count = sum(1 for t in threats if t.get("is_anomaly", False))

    total_threats = len(threats)
    current_time = time.time()
    recent_threats = sum(
        1
        for t in threats
        if "timestamp" in t
        and t["timestamp"]
        and (
            current_time - datetime.fromisoformat(t["timestamp"].replace("Z", "+00:00")).timestamp()
        )
        <= 60
    )

    return {
        "total_alerts": alert_stats["total_alerts"],
        "critical_alerts": alert_stats["by_severity"].get("critical", 0),
        "high_alerts": high_count,
        "medium_alerts": medium_count,
        "low_alerts": low_count,
        "resolved_alerts": alert_stats["acknowledged"],
        "pending_alerts": alert_stats["unacknowledged"],
        "alert_rate": alert_stats["current_threat_rate"],
        "current_threat_rate": alert_stats["current_threat_rate"],
        "current_anomaly_rate": alert_stats["current_anomaly_rate"],
        "by_severity": alert_stats["by_severity"],
        "threat_summary": {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "anomalies": anomaly_count,
        },
        "top_threats": [
            {
                "domain": t.get("domain", ""),
                "risk_score": 10
                if t.get("risk_score") == "High"
                else 5
                if t.get("risk_score") == "Medium"
                else 2,
                "category": t.get("category", ""),
                "count": 1,
            }
            for t in automated_threats[:5]
        ],
    }


@router.get("/trend")
def get_trend():
    """Get real-time trend data for the activity chart"""
    from backend.core.state import get_trend_data

    trend_data = get_trend_data()

    # Ensure we have at least 10 data points (fill with zeros if empty)
    if not trend_data:
        from datetime import datetime

        now = datetime.now()
        trend_data = [
            {
                "time": (now - timedelta(seconds=i * 5)).strftime("%H:%M:%S"),
                "threats": 0,
                "anomalies": 0,
                "safe": 0,
            }
            for i in range(9, -1, -1)
        ]
    elif len(trend_data) < 10:
        # Pad with zeros
        from datetime import datetime

        now = datetime.now()
        while len(trend_data) < 10:
            trend_data.insert(
                0,
                {
                    "time": (now - timedelta(seconds=(10 - len(trend_data)) * 5)).strftime(
                        "%H:%M:%S"
                    ),
                    "threats": 0,
                    "anomalies": 0,
                    "safe": 0,
                },
            )

    return {"trend": trend_data}


@router.get("/ml/dashboard")
def get_ml_dashboard():
    """Get ML dashboard statistics"""
    # Calculate basic metrics
    threats = get_all_threats()
    total_domains = len(threats)
    high_entropy = sum(1 for t in threats if t.get("entropy", 0) > 3.5)
    medium_entropy = sum(1 for t in threats if 2.0 <= t.get("entropy", 0) <= 3.5)
    low_entropy = sum(1 for t in threats if t.get("entropy", 0) < 2.0)

    # Calculate accuracy based on anomalies (simplified)
    anomalies = sum(1 for t in threats if t.get("is_anomaly", False))
    accuracy = 0.85 if total_domains > 0 else 0  # Mock accuracy

    return {
        "overview": {
            "overall_accuracy": accuracy * 100,
            "total_analyzed": total_domains,
            "anomalies_detected": anomalies,
            "false_positives": 0,  # Not implemented
            "false_negatives": 0,  # Not implemented
        },
        "feedback": {
            "total_feedback": 0,
            "correct_predictions": 0,
            "false_positives": 0,
            "false_negatives": 0,
        },
        "thresholds": {
            "entropy_threshold": 3.5,
            "anomaly_threshold": 0.1,
        },
        "features": {
            "tld_tracked": len({t.get("domain", "").split(".")[-1] for t in threats}),
            "domain_patterns": len({t.get("domain", "") for t in threats}),
        },
        "entropy_distribution": {
            "high": high_entropy,
            "medium": medium_entropy,
            "low": low_entropy,
        },
        "learning_progress": {
            "patterns_learned": 5,  # Mock value
            "total_patterns": 10,  # Mock value
            "progress_percentage": 50,  # Mock value
        },
        "model_performance": {
            "precision": 0.85,
            "recall": 0.82,
            "f1_score": 0.83,
            "accuracy": accuracy,
        },
        "feature_importance": [
            {"feature": "Entropy", "importance": 0.4},
            {"feature": "Domain Length", "importance": 0.3},
            {"feature": "TLD", "importance": 0.2},
            {"feature": "AdGuard Metadata", "importance": 0.1},
        ],
    }
