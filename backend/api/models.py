from pydantic import BaseModel
from typing import Optional, List

class AnalysisRequest(BaseModel):
    model_config = {'protected_namespaces': ()}
    domain: str
    registrar: Optional[str] = None
    age: Optional[str] = None
    organization: Optional[str] = None
    model_id: Optional[str] = None

class ChatRequest(BaseModel):
    model_config = {'protected_namespaces': ()}
    message: str
    model_id: Optional[str] = None

class ThreatEntry(BaseModel):
    model_config = {'protected_namespaces': ()}
    domain: str
    risk_score: str
    category: str
    summary: str
    is_anomaly: bool = False
    anomaly_score: float = 0.0
