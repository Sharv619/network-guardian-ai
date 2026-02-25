"""
ML Enhancement API Endpoints.

Provides endpoints for:
- Feedback submission (false positive/negative reporting)
- Feature engineering insights
- Adaptive threshold monitoring
- Model retraining triggers
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.core.deps import AuthenticatedUser, require_authentication
from backend.core.logging_config import get_logger
from backend.logic.adaptive_thresholds import adaptive_thresholds
from backend.logic.feature_engineering import feature_engine
from backend.logic.feedback_loop import feedback_loop
from backend.services.db_logger import db_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ml", tags=["ml"])


class FeedbackRequest(BaseModel):
    domain_id: int = Field(..., description="ID of the domain entry")
    domain: str = Field(..., description="Domain name")
    feedback_type: str = Field(..., description="Type: false_positive, false_negative, or correct")
    original_category: str = Field(..., description="Original classification")
    original_risk: str = Field(..., description="Original risk score")
    corrected_category: str | None = Field(None, description="Correct category (if applicable)")
    corrected_risk: str | None = Field(None, description="Correct risk (if applicable)")
    user_note: str | None = Field(None, description="Optional note")


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    triggered_retrain: bool = False
    metrics: dict[str, Any] | None = None


class DomainFeaturesRequest(BaseModel):
    domain: str = Field(..., description="Domain to analyze")


class ApplyCorrectionsResponse(BaseModel):
    applied: int
    message: str
    retrain_count: int


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest,
    user: AuthenticatedUser = Depends(require_authentication),
) -> FeedbackResponse:
    """Submit feedback on a domain classification."""
    if req.feedback_type not in ["false_positive", "false_negative", "correct"]:
        raise HTTPException(
            status_code=400,
            detail="feedback_type must be: false_positive, false_negative, or correct",
        )

    result = feedback_loop.record_feedback(
        domain=req.domain,
        domain_id=req.domain_id,
        feedback_type=req.feedback_type,
        original_category=req.original_category,
        original_risk=req.original_risk,
        corrected_category=req.corrected_category,
        corrected_risk=req.corrected_risk,
        user_note=req.user_note,
    )

    logger.info(
        "Feedback submitted",
        extra={
            "domain": req.domain,
            "type": req.feedback_type,
            "user": user.identity,
        },
    )

    return FeedbackResponse(
        success=result.success,
        message=result.message,
        triggered_retrain=result.triggered_retrain,
        metrics=result.metrics,
    )


@router.get("/feedback/metrics")
async def get_feedback_metrics(
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Get current feedback metrics."""
    return feedback_loop.get_metrics()


@router.get("/feedback/recent")
async def get_recent_feedback(
    limit: int = 20,
    user: AuthenticatedUser = Depends(require_authentication),
) -> list[dict[str, Any]]:
    """Get recent feedback entries."""
    return feedback_loop.get_recent_feedback(limit=limit)


@router.post("/feedback/apply-corrections", response_model=ApplyCorrectionsResponse)
async def apply_corrections(
    user: AuthenticatedUser = Depends(require_authentication),
) -> ApplyCorrectionsResponse:
    """Apply pending corrections to the model (admin recommended)."""
    result = await feedback_loop.apply_corrections()

    logger.info(
        "Corrections applied",
        extra={"applied": result["applied"], "user": user.identity},
    )

    return ApplyCorrectionsResponse(
        applied=result["applied"],
        message=result["message"],
        retrain_count=result.get("retrain_count", 0),
    )


@router.post("/features/analyze")
async def analyze_domain_features(
    req: DomainFeaturesRequest,
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Analyze domain with enhanced feature engineering."""
    features = feature_engine.extract_features(req.domain)
    temporal = feature_engine.get_temporal_context()
    risk_analysis = feature_engine.calculate_enhanced_risk_score(req.domain, features, temporal)

    return {
        "domain": req.domain,
        "features": {
            "tld": features.tld,
            "tld_reputation": features.tld_reputation,
            "length": features.length,
            "entropy": features.entropy,
            "digit_ratio": features.digit_ratio,
            "vowel_ratio": features.vowel_ratio,
            "hyphen_count": features.hyphen_count,
            "subdomain_count": features.subdomain_count,
            "has_www": features.has_www,
            "suspicious_keyword_score": features.suspicious_keyword_score,
            "brand_impersonation_risk": features.brand_impersonation_risk,
            "is_ip_address": features.is_ip_address,
            "has_punycode": features.has_punycode,
        },
        "temporal_context": {
            "hour_of_day": temporal.hour_of_day,
            "day_of_week": temporal.day_of_week,
            "is_business_hours": temporal.is_business_hours,
            "is_weekend": temporal.is_weekend,
            "risk_multiplier": temporal.risk_multiplier,
            "historical_threat_rate": temporal.historical_threat_rate,
        },
        "risk_analysis": risk_analysis,
    }


@router.get("/features/tld-report")
async def get_tld_report(
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Get TLD reputation report."""
    return feature_engine.get_tld_report()


@router.get("/features/temporal-report")
async def get_temporal_report(
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Get temporal pattern report."""
    return feature_engine.get_temporal_report()


@router.get("/thresholds")
async def get_adaptive_thresholds(
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Get adaptive threshold statistics."""
    return adaptive_thresholds.get_stats()


@router.get("/dashboard")
async def get_ml_dashboard(
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Get comprehensive ML dashboard data."""
    feedback_metrics = feedback_loop.get_metrics()
    threshold_stats = adaptive_thresholds.get_stats()
    tld_report = feature_engine.get_tld_report()
    temporal_report = feature_engine.get_temporal_report()
    db_stats = db_logger.get_stats()

    total_decisions = (
        feedback_metrics["false_positives"]
        + feedback_metrics["false_negatives"]
        + feedback_metrics["correct_predictions"]
    )
    overall_accuracy = (
        feedback_metrics["correct_predictions"] / total_decisions if total_decisions > 0 else 1.0
    )

    return {
        "overview": {
            "system_health": "HEALTHY" if overall_accuracy >= 0.8 else "NEEDS_TUNING",
            "overall_accuracy": round(overall_accuracy * 100, 1),
            "total_feedback": feedback_metrics["total_feedback"],
            "pending_retrain": feedback_metrics["pending_retrain"],
            "retrain_count": feedback_metrics["retrain_count"],
        },
        "feedback": feedback_metrics,
        "thresholds": {
            "entropy_threshold": threshold_stats["entropy_threshold"],
            "contamination_rate": threshold_stats["contamination_rate"],
            "entropy_samples": threshold_stats["entropy_samples"],
            "adjustments_count": threshold_stats["adjustments_count"],
            "last_adjustment": threshold_stats.get("last_adjustment"),
        },
        "features": {
            "tld_tracked": tld_report["tracked_tlds"],
            "high_risk_tlds": len(tld_report["high_risk"]),
            "peak_threat_hours": temporal_report["peak_hours"][:3],
            "peak_threat_days": temporal_report["peak_days"][:3],
        },
        "database": {
            "total_domains": db_stats.get("total_domains", 0),
            "total_anomalies": db_stats.get("total_anomalies", 0),
            "categories": db_stats.get("categories", {}),
        },
    }
