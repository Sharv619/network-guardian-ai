
from pydantic import BaseModel
from typing import Optional, List

class AnalysisRequest(BaseModel):
    domain: str
    registrar: Optional[str] = None
    age: Optional[str] = None
    organization: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

class ThreatEntry(BaseModel):
    domain: str
    risk_score: str
    category: str
    summary: str
    timestamp: str
