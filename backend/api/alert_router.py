from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.alerting import AlertSeverity, AlertType, alert_manager
from backend.core.deps import AuthenticatedUser, require_authentication
from backend.core.notification_config import notification_config
from backend.core.notification_service import notification_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    message: str
    details: dict[str, Any]
    timestamp: str
    acknowledged: bool
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str | None = None


class AlertStatsResponse(BaseModel):
    total_alerts: int
    acknowledged: int
    unacknowledged: int
    by_severity: dict[str, int]
    current_threat_rate: int
    current_anomaly_rate: int
    current_api_failure_rate: float


@router.get("", response_model=list[AlertResponse])
def get_alerts(
    severity: str | None = Query(None, description="Filter by severity"),
    alert_type: str | None = Query(None, description="Filter by alert type"),
    acknowledged: bool | None = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return"),
) -> list[AlertResponse]:
    """Get alerts with optional filtering."""
    sev_filter = AlertSeverity(severity) if severity else None
    type_filter = AlertType(alert_type) if alert_type else None

    alerts = alert_manager.get_alerts(
        severity=sev_filter,
        alert_type=type_filter,
        acknowledged=acknowledged,
        limit=limit,
    )

    return [AlertResponse(**a.to_dict()) for a in alerts]


@router.get("/stats", response_model=AlertStatsResponse)
def get_alert_stats() -> AlertStatsResponse:
    """Get alert statistics."""
    return AlertStatsResponse(**alert_manager.get_stats())


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeRequest,
) -> AlertResponse:
    """Acknowledge an alert."""
    alert = alert_manager.acknowledge_alert(alert_id, request.acknowledged_by)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return AlertResponse(**alert.to_dict())


@router.post("/check")
async def check_thresholds() -> dict[str, Any]:
    """Manually trigger threshold check and return any new alerts."""
    alerts = await alert_manager.check_thresholds()
    return {
        "triggered": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.delete("")
def clear_alerts() -> dict[str, str]:
    """Clear all alerts (use with caution)."""
    alert_manager.clear_alerts()
    return {"status": "cleared"}


@router.get("/severities")
def get_severities() -> list[str]:
    """Get available alert severities."""
    return [s.value for s in AlertSeverity]


@router.get("/types")
def get_alert_types() -> list[str]:
    """Get available alert types."""
    return [t.value for t in AlertType]


class ChannelConfigRequest(BaseModel):
    enabled: bool
    settings: dict[str, Any]


class NotificationEnableRequest(BaseModel):
    enabled: bool


class ChannelTestResponse(BaseModel):
    success: bool
    message: str


@router.get("/notifications/config")
def get_notification_config(
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Get notification configuration (sensitive data masked)."""
    return notification_config.to_dict()


@router.post("/notifications/config")
def update_notification_config(
    config: NotificationEnableRequest,
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Enable or disable all notifications."""
    notification_config.set_enabled(config.enabled)
    return {"success": True, "enabled": config.enabled}


@router.post("/notifications/channel/{channel_name}")
def update_channel_config(
    channel_name: str,
    config: ChannelConfigRequest,
    user: AuthenticatedUser = Depends(require_authentication),
) -> dict[str, Any]:
    """Configure a specific notification channel."""
    valid_channels = ["email", "slack", "discord", "webhook"]
    if channel_name not in valid_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel. Must be one of: {valid_channels}",
        )

    notification_config.update_channel(
        channel_name=channel_name,
        enabled=config.enabled,
        settings=config.settings,
    )

    return {
        "success": True,
        "channel": channel_name,
        "enabled": config.enabled,
    }


@router.get("/notifications/channel/{channel_name}/test", response_model=ChannelTestResponse)
async def test_channel(
    channel_name: str,
    user: AuthenticatedUser = Depends(require_authentication),
) -> ChannelTestResponse:
    """Test a notification channel configuration."""
    result = await notification_service.test_channel(channel_name)
    return ChannelTestResponse(**result)
