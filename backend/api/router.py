
from fastapi import APIRouter
import time
from typing import List
from .models import AnalysisRequest, ThreatEntry, ChatRequest
from ..services.gemini_analyzer import analyze_domain, chat_with_ai
from ..services.sheets_logger import log_threat_to_sheet, fetch_recent_from_sheets
from ..services.adguard_poller import processed_domains
from ..core.state import automated_threats, manual_scans

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "processed_count": len(processed_domains)}

@router.post("/analyze")
def api_analyze(req: AnalysisRequest):
    """Manual analysis endpoint."""
    print(f"DEBUG: Manual Scan triggered for: {req.domain}")
    context = {}
    if req.registrar: context['Registrar'] = req.registrar
    if req.age: context['Age'] = req.age
    
    analysis = analyze_domain(req.domain, context)
    
    # Push manual scans to Sheets (Ecosystem Optimization)
    log_threat_to_sheet(req.domain, analysis)
    
    # Update Live Memory - Single Source of Truth for Research
    new_entry = {
        "domain": req.domain,
        "risk_score": analysis.get("risk_score"),
        "category": analysis.get("category"),
        "summary": analysis.get("summary"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    manual_scans.insert(0, new_entry)
    if len(manual_scans) > 50: 
        manual_scans.pop()
    
    return analysis

@router.post("/chat")
def api_chat(req: ChatRequest):
    """BFF Chat endpoint."""
    response = chat_with_ai(req.message)
    return {"text": response}

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
