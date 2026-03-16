from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    model_config = {'protected_namespaces': ()}
    domain: str
    registrar: str | None = None
    age: str | None = None
    organization: str | None = None
    model_id: str | None = None


class ChatRequest(BaseModel):
    model_config = {'protected_namespaces': ()}
    message: str
    model_id: str | None = None


class ThreatEntry(BaseModel):
    model_config = {'protected_namespaces': ()}
    domain: str
    risk_score: str
    category: str
    summary: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    is_anomaly: bool = False
    anomaly_score: float = 0.0
    adguard_metadata: dict = Field(default_factory=dict)
    analysis_source: str = "unknown"
    entropy: float = 0.0
