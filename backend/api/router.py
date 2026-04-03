from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..core.state import manual_scans
from ..db.database import get_session
from ..db.models import ThreatEntry
from ..db.repository import DomainRepository, get_domain_repository
from .advanced_chat import router as advanced_chat_router
from .chat import router as chat_router

router = APIRouter()


@router.get("/health")
def api_health():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "message": "Network Guardian API is running",
        "features": [
            "• Real-time threat detection",
            "• Manual domain analysis",
            "• Threat history tracking",
            "• Automated scanning",
            "• Threat detection logic",
        ],
    }


@router.get("/history")
async def api_history(request: Request):
    """Get all threat history - database + live combined."""
    from ..core.state import automated_threats

    # Get tenant_id from request state
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get repository for database domains
    repo = await get_domain_repository(tenant_id=tenant_id)
    db_domains = await repo.get_all_domains()

    # Convert database domains to dict (keyed by domain)
    all_threats: dict[str, dict] = {}
    for domain in db_domains:
        ts = domain.timestamp.isoformat() if domain.timestamp else None
        all_threats[domain.domain] = {
            "domain": domain.domain,
            "risk_score": domain.risk_score,
            "category": domain.category,
            "summary": domain.summary,
            "timestamp": ts,
            "is_anomaly": domain.is_anomaly,
            "anomaly_score": domain.anomaly_score,
            "entropy": domain.entropy,
        }

    # Add live automated_threats - overwrites DB entries for same domain
    for threat in automated_threats:
        domain = threat.get("domain", "")
        if domain:
            all_threats[domain] = {
                "domain": domain,
                "risk_score": threat.get("risk_score", "Unknown"),
                "category": threat.get("category", "Unknown"),
                "summary": threat.get("summary"),
                "timestamp": threat.get("timestamp"),
                "is_anomaly": threat.get("is_anomaly", False),
                "anomaly_score": threat.get("anomaly_score", 0.0),
                "entropy": threat.get("entropy"),
            }

    # Convert to list and sort by timestamp (newest first)
    threat_list = list(all_threats.values())
    threat_list.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "", reverse=True)

    return threat_list


@router.get("/manual-history")
def api_manual_history():
    """Get manual analysis session history."""
    result = []
    for item in manual_scans:
        threat_entry = ThreatEntry(**item)
        result.append(threat_entry.dict())
    return result


@router.get("/test-report")
def get_test_report():
    """Get automated test report status."""
    return {
        "status": "success",
        "passed": 0,
        "failed": 0,
        "total": 0,
        "summary": "Test report not available",
        "details": "Automated testing is not configured",
    }


@router.post("/analyze")
async def api_analyze(request: Request, analysis_request: dict[str, Any]):
    """Analyze a domain for security threats and store the result."""
    domain = analysis_request.get("domain")
    if not domain:
        raise HTTPException(status_code=422, detail="Domain is required")
    if len(domain) > 255:
        raise HTTPException(status_code=422, detail="Domain too long")

    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility

    model_id = analysis_request.get("model_id")

    # Use Ollama for analysis (fully local)
    from backend.services.ollama_analyzer import analyze_with_ollama

    ollama_model = model_id.replace("ollama:", "") if model_id else None
    analysis = analyze_with_ollama(domain, model=ollama_model)

    if not analysis:
        raise HTTPException(status_code=500, detail="Analysis failed")

    # Ensure timestamp is included in the response
    if "timestamp" not in analysis:
        analysis["timestamp"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Add tenant_id to the analysis for storage
    analysis["tenant_id"] = tenant_id

    # Update real-time trend data
    from backend.core.state import update_trend_count

    risk = analysis.get("risk_score", "").lower()
    is_threat = risk in ["high", "medium"]
    is_anomaly = analysis.get("is_anomaly", False)
    is_safe = risk == "low"
    update_trend_count(is_threat=is_threat, is_anomaly=is_anomaly, is_safe=is_safe)

    # Store the analysis in the database for the current tenant
    try:
        async with get_session() as session:
            repo = DomainRepository(session, tenant_id=tenant_id)
            result = await repo.create_domain_from_analysis(analysis)
            print(f"DEBUG: Saved domain {domain}, result: {result}")
    except Exception as e:
        print(f"Warning: Failed to store analysis for domain {domain}: {e}")

    return analysis


# Mount the chat routers
router.include_router(chat_router, prefix="", tags=["chat"])
router.include_router(advanced_chat_router, prefix="", tags=["advanced-chat"])
