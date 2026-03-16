from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from ..core.state import automated_threats, manual_scans
from ..db.models import ThreatEntry
from ..services.gemini_analyzer import analyze_domain
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
def api_history():
    """Get recent threat history from automated threats."""
    # Ensure all timestamps are properly formatted
    for item in automated_threats:
        if "timestamp" in item and item["timestamp"]:
            # Ensure ISO-8601 format
            if not item["timestamp"].endswith("Z"):
                item["timestamp"] = item["timestamp"].replace("+00:00", "Z")
        else:
            # Fallback to current time if missing
            item["timestamp"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Convert to ThreatEntry objects
    result = []
    for item in automated_threats:
        threat_entry = ThreatEntry(**item)
        result.append(threat_entry.dict())

    return result


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
def api_analyze(request: dict[str, Any]):
    """Analyze a domain for security threats."""
    domain = request.get("domain")
    if not domain:
        raise HTTPException(status_code=422, detail="Domain is required")
    if len(domain) > 255:
        raise HTTPException(status_code=422, detail="Domain too long")

    try:
        analysis = analyze_domain(domain)
        # Ensure timestamp is included in the response
        if "timestamp" not in analysis:
            analysis["timestamp"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mount the chat routers
router.include_router(chat_router, prefix="", tags=["chat"])
router.include_router(advanced_chat_router, prefix="", tags=["advanced-chat"])
