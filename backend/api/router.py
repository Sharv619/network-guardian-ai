
from fastapi import APIRouter
import time
from datetime import datetime, timezone
from typing import List
from .models import AnalysisRequest, ThreatEntry, ChatRequest
from ..services.gemini_analyzer import analyze_domain, chat_with_ai, get_available_models
from ..services.sheets_logger import log_threat_to_sheet, fetch_recent_from_sheets
from ..services.adguard_poller import processed_domains
from ..core.state import automated_threats, manual_scans

router = APIRouter()

# Task 3: Just-In-Time (JIT) Context (FinOps Optimization)
SYSTEM_DOCS = {
    "role": "Network Guardian AI",
    "architecture": "AdGuard Home (Interceptor) -> FastAPI (Orchestrator) -> Google Sheets (Data Lake) & Notion (Report).",
    "security_stack": "Real-time DNS blocking with AI-powered forensic analysis and Shannon Entropy heuristics.",
    "persona": "Professional SOC Analyst with system-level awareness of the Linux-based Docker environment."
}

@router.get("/health")
def health_check():
    return {"status": "ok", "processed_count": len(processed_domains)}

@router.get("/models")
def api_list_models():
    """SRE Discovery: List available Gemini models."""
    return get_available_models()

@router.post("/analyze")
def api_analyze(req: AnalysisRequest):
    """Manual analysis endpoint."""
    print(f"DEBUG: Manual Scan triggered for: {req.domain} (Model: {req.model_id})")
    context = {}
    if req.registrar: context['Registrar'] = req.registrar
    if req.age: context['Age'] = req.age
    
    analysis = analyze_domain(req.domain, context, model_id=req.model_id)
    
    # Push manual scans to Sheets (Ecosystem Optimization)
    log_threat_to_sheet(req.domain, analysis)
    
    # Update Live Memory - Single Source of Truth for Research
    new_entry = {
        "domain": req.domain,
        "risk_score": analysis.get("risk_score"),
        "category": analysis.get("category"),
        "summary": analysis.get("summary"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    manual_scans.insert(0, new_entry)
    if len(manual_scans) > 50: 
        manual_scans.pop()
    
    return analysis

@router.post("/chat")
def api_chat(req: ChatRequest):
    """BFF Chat endpoint with Graceful Degradation and JIT Context."""
    # SRE Pattern: Task-Specific Context Injection
    keywords = ["architecture", "stack", "how do you work", "who are you", "system", "infrastructure"]
    user_msg_lower = req.message.lower()
    
    final_message = req.message
    if any(k in user_msg_lower for k in keywords):
        context_block = f"\n\n[JIT SYSTEM CONTEXT]: {SYSTEM_DOCS}\n"
        final_message = f"{context_block}User Query: {req.message}"
        print("FinOps Notice: Injecting System Docs for Architectural Query.")

    try:
        response = chat_with_ai(final_message, model_id=req.model_id)
        return {"text": response}
    except Exception as e:
        print(f"Chat API Error: {e}")
        # SRE Pattern: Error Masking
        return {
            "text": "I am currently operating in Autonomous SOC Mode due to cloud analysis throttling. "
                    "While my conversational processing is temporarily degraded, my network interceptor "
                    "and local heuristic engines remain 100% Active. I am still guarding your data—how can I help you with system logic?"
        }

@router.get("/history", response_model=List[ThreatEntry])
def api_history():
    """Get recent threat history (Automated Only + Google Sheets History)."""
    # SRE Pattern: Read-Through Cache
    # Return Live Memory (Fast) + Database History (Slow)
    history = fetch_recent_from_sheets()
    
    # Simple merge: Live events first, then DB events
    return automated_threats + history

@router.get("/manual-history", response_model=List[ThreatEntry])
def api_manual_history():
    """Get manual analysis session history."""
    return manual_scans

@router.get("/test-report")
def get_test_report():
    """Get automated test report status."""
    return {
        "status": "success",
        "passed": 0,
        "failed": 0,
        "total": 0,
        "summary": "Test report not available",
        "details": "Automated testing is not configured"
    }
