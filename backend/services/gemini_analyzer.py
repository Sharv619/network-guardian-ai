from google import genai
from google.genai import types
import json
import os
import re
from typing import Dict, Any, Optional
from ..core.config import settings
from ..logic.ml_heuristics import calculate_entropy
from pydantic import BaseModel

# SRE Update: Switch to modern google-genai SDK
client = None
if settings.GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ SDK Init Error: {e}")

class ThreatVerdict(BaseModel):
    risk_score: str # "Low" | "Medium" | "High"
    category: str
    summary: str

SYSTEM_INSTRUCTION = """## ROLE
You are the "Network Guardian AI," a world-class cybersecurity agent and SOC Analyst. You monitor a security stack consisting of AdGuard Home (Interceptor), Google Sheets (Data Lake), and FastAPI (Orchestrator).

## CONTEXT: THE SYSTEM ARCHITECTURE
1. Interceptor: AdGuard Home blocks malicious domains at the DNS level.
2. Orchestrator: A Python/FastAPI backend polls AdGuard every 30-60 seconds.
3. Data Lake: Google Sheets stores every unique block for long-term audit logs.
4. Report: Notion Database provides a high-level executive summary of threat levels.

## PERSONALITY
- Tone: Technical, helpful, professional, and slightly "SOC Analyst" focused.
- Safety: Focus strictly on defense. Never provide offensive malware instructions.
- Format: Use Markdown for all responses (bolding, lists, and code blocks)."""

def analyze_domain(domain: str, context: Optional[Dict[str, Any]] = None) -> dict:
    context_str = f" Context: {context}" if context else ""
    prompt = f"Analyze this domain for security risks: {domain}{context_str}"
    
    if not client:
        return _heuristic_fallback(domain, "SDK Not Initialized")

    try:
        # Use stable gemini-2.0-flash (fastest/cheapest)
        # SRE Pattern: Robust JSON Extraction using SDK schemas
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type='application/json',
                response_schema=ThreatVerdict,
            )
        )
        
        # The new SDK parses the JSON directly if response_schema is provided
        return response.parsed.model_dump()
    except Exception as e:
        print(f"Gemini Analysis Failed: {e}. Falling back to Heuristics.")
        return _heuristic_fallback(domain, str(e))

def chat_with_ai(message: str) -> str:
    if not client:
        return "Network Guardian AI: Engine not initialized. Please check your API keys."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        return response.text
    except Exception as e:
        return f"Network Guardian AI: Error processing request: {str(e)}"

def _heuristic_fallback(domain: str, error: str) -> dict:
    entropy = calculate_entropy(domain)
    if entropy > 3.5:
        return {
            "risk_score": "High",
            "category": "Malicious Pattern",
            "summary": f"AI Fail ({error[:20]}). Fallback: High Entropy ({entropy:.2f})."
        }
    else:
        return {
            "risk_score": "Low",
            "category": "Unknown",
            "summary": f"AI Fail ({error[:20]}). Fallback: Low Entropy ({entropy:.2f})."
        }