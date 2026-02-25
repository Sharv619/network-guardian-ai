import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    HIGH_THREAT_RATE = "high_threat_rate"
    ANOMALY_SPIKE = "anomaly_spike"
    API_FAILURE = "api_failure"
    GEMINI_QUOTA_EXHAUSTED = "gemini_quota_exhausted"
    HIGH_ERROR_RATE = "high_error_rate"
    SYSTEM_RESOURCE = "system_resource"


@dataclass
class Alert:
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
        }


async def _broadcast_alert(alert: Alert) -> None:
    """Broadcast alert to WebSocket clients (non-blocking)."""
    try:
        from backend.core.websocket_manager import ws_manager, EventType

        await ws_manager.broadcast(
            event_type=EventType.ALERT_CREATED,
            data=alert.to_dict(),
            channel="alerts",
        )
    except Exception as e:
        logger.warning("Failed to broadcast alert", extra={"error": str(e)})


async def _broadcast_acknowledgement(alert: Alert) -> None:
    """Broadcast alert acknowledgement to WebSocket clients."""
    try:
        from backend.core.websocket_manager import ws_manager, EventType

        await ws_manager.broadcast(
            event_type=EventType.ALERT_ACKNOWLEDGED,
            data=alert.to_dict(),
            channel="alerts",
        )
    except Exception as e:
        logger.warning("Failed to broadcast acknowledgement", extra={"error": str(e)})


class AlertManager:
    """Centralized alert management with threshold checking and webhook support."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        high_threat_rate_threshold: float = 10.0,
        anomaly_spike_threshold: float = 5.0,
        api_failure_rate_threshold: float = 0.1,
        system_cpu_threshold: float = 90.0,
        system_memory_threshold: float = 90.0,
    ) -> None:
        self.webhook_url = webhook_url
        self.high_threat_rate_threshold = high_threat_rate_threshold
        self.anomaly_spike_threshold = anomaly_spike_threshold
        self.api_failure_rate_threshold = api_failure_rate_threshold
        self.system_cpu_threshold = system_cpu_threshold
        self.system_memory_threshold = system_memory_threshold

        self.alerts: list[Alert] = []
        self.max_alerts = 1000

        self._threat_timestamps: list[float] = []
        self._anomaly_timestamps: list[float] = []
        self._api_calls: list[tuple[float, bool]] = []

        self._http_client: Optional[httpx.AsyncClient] = None

    async def init_client(self) -> None:
        """Initialize HTTP client for webhook calls."""
        if self.webhook_url and not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=10.0)

    async def close_client(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _generate_alert_id(self) -> str:
        import uuid

        return str(uuid.uuid4())[:8]

    async def _send_webhook(self, alert: Alert) -> bool:
        """Send alert to configured webhook URL."""
        if not self.webhook_url or not self._http_client:
            return False

        try:
            payload = {
                "alert": alert.to_dict(),
                "source": "network-guardian-ai",
            }
            response = await self._http_client.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code >= 200 and response.status_code < 300:
                logger.info("Webhook alert sent", extra={"alert_id": alert.id})
                return True
            else:
                logger.warning(
                    "Webhook alert failed",
                    extra={"alert_id": alert.id, "status_code": response.status_code},
                )
                return False
        except Exception as e:
            logger.error("Webhook error", extra={"error": str(e), "alert_id": alert.id})
            return False

    def _send_webhook_sync(self, alert: Alert) -> bool:
        """Send alert to configured webhook URL (sync version)."""
        if not self.webhook_url:
            return False

        try:
            import requests
            payload = {
                "alert": alert.to_dict(),
                "source": "network-guardian-ai",
            }
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code >= 200 and response.status_code < 300:
                logger.info("Webhook alert sent", extra={"alert_id": alert.id})
                return True
            else:
                logger.warning(
                    "Webhook alert failed",
                    extra={"alert_id": alert.id, "status_code": response.status_code},
                )
                return False
        except Exception as e:
            logger.error("Webhook error", extra={"error": str(e), "alert_id": alert.id})
            return False

    async def _send_notifications(self, alert: Alert) -> None:
        """Send notifications via configured channels."""
        try:
            from backend.core.notification_service import notification_service

            results = await notification_service.send_alert_notification(alert)
            if results:
                logger.info(
                    "Notifications sent",
                    extra={"alert_id": alert.id, "results": results},
                )
        except Exception as e:
            logger.warning(
                "Notification service error",
                extra={"alert_id": alert.id, "error": str(e)},
            )

    def _add_alert(self, alert: Alert) -> None:
        """Add alert to in-memory storage."""
        self.alerts.insert(0, alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts.pop()

    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> Alert:
        """Create and store a new alert."""
        alert = Alert(
            id=self._generate_alert_id(),
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {},
        )

        self._add_alert(alert)
        logger.warning(
            "Alert created",
            extra={
                "alert_id": alert.id,
                "alert_type": alert_type.value,
                "severity": severity.value,
                "alert_message": message,
            },
        )

        await self._send_webhook(alert)
        await _broadcast_alert(alert)
        await self._send_notifications(alert)

        return alert

    def create_alert_sync(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> Alert:
        """Create and store a new alert (sync version)."""
        # Handle string inputs for backward compatibility
        if isinstance(alert_type, str):
            alert_type = AlertType(alert_type)
        if isinstance(severity, str):
            severity = AlertSeverity(severity)
            
        alert = Alert(
            id=self._generate_alert_id(),
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {},
        )

        self._add_alert(alert)
        logger.warning(
            "Alert created",
            extra={
                "alert_id": alert.id,
                "alert_type": alert_type.value,
                "severity": severity.value,
                "alert_message": message,
            },
        )

        # Use sync webhook version
        self._send_webhook_sync(alert)
        
        # Note: WebSocket broadcasting and notifications are async-only
        # In sync contexts, we skip these for simplicity

        return alert

    def record_threat(self) -> None:
        """Record a threat detection for rate monitoring."""
        self._threat_timestamps.append(time.time())
        self._cleanup_old_timestamps(self._threat_timestamps, window=60.0)

    def record_anomaly(self) -> None:
        """Record an anomaly detection for spike monitoring."""
        self._anomaly_timestamps.append(time.time())
        self._cleanup_old_timestamps(self._anomaly_timestamps, window=60.0)

    def record_api_call(self, success: bool) -> None:
        """Record an API call result for failure rate monitoring."""
        self._api_calls.append((time.time(), success))
        self._cleanup_old_api_calls(window=60.0)

    def _cleanup_old_timestamps(self, timestamps: list[float], window: float = 60.0) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.time() - window
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

    def _cleanup_old_api_calls(self, window: float = 60.0) -> None:
        """Remove API calls older than the window."""
        cutoff = time.time() - window
        while self._api_calls and self._api_calls[0][0] < cutoff:
            self._api_calls.pop(0)

    async def check_thresholds(self) -> list[Alert]:
        """Check all thresholds and create alerts if needed."""
        alerts = []

        threat_count = len(self._threat_timestamps)
        if threat_count >= self.high_threat_rate_threshold:
            alert = await self.create_alert(
                AlertType.HIGH_THREAT_RATE,
                AlertSeverity.HIGH,
                f"High threat rate detected: {threat_count} threats in the last minute",
                {"threat_count": threat_count, "threshold": self.high_threat_rate_threshold},
            )
            alerts.append(alert)

        anomaly_count = len(self._anomaly_timestamps)
        if anomaly_count >= self.anomaly_spike_threshold:
            alert = await self.create_alert(
                AlertType.ANOMALY_SPIKE,
                AlertSeverity.MEDIUM,
                f"Anomaly spike detected: {anomaly_count} anomalies in the last minute",
                {"anomaly_count": anomaly_count, "threshold": self.anomaly_spike_threshold},
            )
            alerts.append(alert)

        if self._api_calls:
            success_count = sum(1 for _, s in self._api_calls if s)
            failure_count = len(self._api_calls) - success_count
            failure_rate = failure_count / len(self._api_calls) if self._api_calls else 0

            if failure_rate >= self.api_failure_rate_threshold:
                alert = await self.create_alert(
                    AlertType.API_FAILURE,
                    AlertSeverity.HIGH,
                    f"High API failure rate: {failure_rate:.1%} failures in the last minute",
                    {
                        "failure_rate": failure_rate,
                        "failure_count": failure_count,
                        "total_calls": len(self._api_calls),
                        "threshold": self.api_failure_rate_threshold,
                    },
                )
                alerts.append(alert)

        return alerts

    async def check_system_resources(
        self, cpu_percent: float, memory_percent: float
    ) -> list[Alert]:
        """Check system resource thresholds."""
        alerts = []

        if cpu_percent >= self.system_cpu_threshold:
            alert = await self.create_alert(
                AlertType.SYSTEM_RESOURCE,
                AlertSeverity.HIGH,
                f"High CPU usage: {cpu_percent:.1f}%",
                {"cpu_percent": cpu_percent, "threshold": self.system_cpu_threshold},
            )
            alerts.append(alert)

        if memory_percent >= self.system_memory_threshold:
            alert = await self.create_alert(
                AlertType.SYSTEM_RESOURCE,
                AlertSeverity.HIGH,
                f"High memory usage: {memory_percent:.1f}%",
                {"memory_percent": memory_percent, "threshold": self.system_memory_threshold},
            )
            alerts.append(alert)

        return alerts

    def acknowledge_alert(
        self, alert_id: str, acknowledged_by: Optional[str] = None
    ) -> Optional[Alert]:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now(timezone.utc)
                alert.acknowledged_by = acknowledged_by
                logger.info(
                    "Alert acknowledged",
                    extra={"alert_id": alert_id, "acknowledged_by": acknowledged_by},
                )
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_broadcast_acknowledgement(alert))
                except RuntimeError:
                    pass
                return alert
        return None

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alerts with optional filtering."""
        filtered = self.alerts

        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        if acknowledged is not None:
            filtered = [a for a in filtered if a.acknowledged == acknowledged]

        return filtered[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get alert statistics."""
        total = len(self.alerts)
        acknowledged = sum(1 for a in self.alerts if a.acknowledged)
        by_severity = {}
        for severity in AlertSeverity:
            by_severity[severity.value] = sum(1 for a in self.alerts if a.severity == severity)

        return {
            "total_alerts": total,
            "acknowledged": acknowledged,
            "unacknowledged": total - acknowledged,
            "by_severity": by_severity,
            "current_threat_rate": len(self._threat_timestamps),
            "current_anomaly_rate": len(self._anomaly_timestamps),
            "current_api_failure_rate": self._get_current_failure_rate(),
        }

    def _get_current_failure_rate(self) -> float:
        """Get current API failure rate."""
        if not self._api_calls:
            return 0.0
        failures = sum(1 for _, s in self._api_calls if not s)
        return failures / len(self._api_calls)

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()
        logger.info("All alerts cleared")


alert_manager = AlertManager()
