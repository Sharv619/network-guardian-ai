import asyncio
import pytest
from datetime import datetime, timezone

from backend.core.alerting import (
    Alert,
    AlertManager,
    AlertSeverity,
    AlertType,
    alert_manager,
)


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self):
        alert = Alert(
            id="test-123",
            alert_type=AlertType.HIGH_THREAT_RATE,
            severity=AlertSeverity.HIGH,
            message="Test alert message",
        )

        assert alert.id == "test-123"
        assert alert.alert_type == AlertType.HIGH_THREAT_RATE
        assert alert.severity == AlertSeverity.HIGH
        assert alert.acknowledged is False

    def test_alert_with_details(self):
        alert = Alert(
            id="detail-456",
            alert_type=AlertType.API_FAILURE,
            severity=AlertSeverity.MEDIUM,
            message="API failure detected",
            details={"endpoint": "/analyze", "status_code": 500},
        )

        assert alert.details["endpoint"] == "/analyze"
        assert alert.details["status_code"] == 500

    def test_alert_to_dict(self):
        alert = Alert(
            id="dict-test",
            alert_type=AlertType.ANOMALY_SPIKE,
            severity=AlertSeverity.LOW,
            message="Test",
            details={"count": 5},
        )

        result = alert.to_dict()

        assert result["id"] == "dict-test"
        assert result["alert_type"] == "anomaly_spike"
        assert result["severity"] == "low"
        assert result["details"]["count"] == 5
        assert result["acknowledged"] is False


class TestAlertManager:
    """Tests for AlertManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh alert manager for testing."""
        return AlertManager(
            webhook_url=None,
            high_threat_rate_threshold=10.0,
            anomaly_spike_threshold=5.0,
            api_failure_rate_threshold=0.1,
        )

    def test_initial_state(self, manager):
        assert len(manager.alerts) == 0
        assert manager.webhook_url is None

    async def test_create_alert(self, manager):
        alert = await manager.create_alert(
            alert_type=AlertType.HIGH_THREAT_RATE,
            severity=AlertSeverity.HIGH,
            message="High threat rate detected",
        )

        assert alert is not None
        assert len(manager.alerts) == 1
        assert alert.alert_type == AlertType.HIGH_THREAT_RATE

    async def test_create_multiple_alerts(self, manager):
        await manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.HIGH, "Alert 1")
        await manager.create_alert(AlertType.ANOMALY_SPIKE, AlertSeverity.MEDIUM, "Alert 2")
        await manager.create_alert(AlertType.API_FAILURE, AlertSeverity.LOW, "Alert 3")

        assert len(manager.alerts) == 3

    def test_record_threat(self, manager):
        for _ in range(5):
            manager.record_threat()

        assert len(manager._threat_timestamps) == 5

    def test_record_anomaly(self, manager):
        for _ in range(3):
            manager.record_anomaly()

        assert len(manager._anomaly_timestamps) == 3

    def test_record_api_call(self, manager):
        manager.record_api_call(True)
        manager.record_api_call(True)
        manager.record_api_call(False)

        assert len(manager._api_calls) == 3

    async def test_check_thresholds_below(self, manager):
        for _ in range(5):
            manager.record_threat()

        alerts = await manager.check_thresholds()

        assert len(alerts) == 0

    async def test_check_thresholds_exceeded(self, manager):
        for _ in range(15):
            manager.record_threat()

        alerts = await manager.check_thresholds()

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HIGH_THREAT_RATE

    async def test_check_anomaly_threshold(self, manager):
        for _ in range(7):
            manager.record_anomaly()

        alerts = await manager.check_thresholds()

        assert any(a.alert_type == AlertType.ANOMALY_SPIKE for a in alerts)

    async def test_check_api_failure_rate(self, manager):
        for _ in range(15):
            manager.record_api_call(False)

        for _ in range(5):
            manager.record_api_call(True)

        alerts = await manager.check_thresholds()

        assert any(a.alert_type == AlertType.API_FAILURE for a in alerts)

    async def test_acknowledge_alert(self, manager):
        alert = await manager.create_alert(
            AlertType.HIGH_THREAT_RATE,
            AlertSeverity.HIGH,
            "Test alert",
        )

        result = manager.acknowledge_alert(alert.id, "admin@example.com")

        assert result is not None
        assert result.acknowledged is True
        assert result.acknowledged_by == "admin@example.com"

    def test_acknowledge_nonexistent_alert(self, manager):
        result = manager.acknowledge_alert("nonexistent-id")

        assert result is None

    def test_get_alerts_all(self, manager):
        asyncio.run(manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.HIGH, "1"))
        asyncio.run(manager.create_alert(AlertType.ANOMALY_SPIKE, AlertSeverity.MEDIUM, "2"))

        alerts = manager.get_alerts()

        assert len(alerts) == 2

    def test_get_alerts_by_severity(self, manager):
        asyncio.run(manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.HIGH, "1"))
        asyncio.run(manager.create_alert(AlertType.ANOMALY_SPIKE, AlertSeverity.MEDIUM, "2"))
        asyncio.run(manager.create_alert(AlertType.API_FAILURE, AlertSeverity.HIGH, "3"))

        alerts = manager.get_alerts(severity=AlertSeverity.HIGH)

        assert len(alerts) == 2

    def test_get_alerts_by_type(self, manager):
        asyncio.run(manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.HIGH, "1"))
        asyncio.run(manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.MEDIUM, "2"))
        asyncio.run(manager.create_alert(AlertType.ANOMALY_SPIKE, AlertSeverity.LOW, "3"))

        alerts = manager.get_alerts(alert_type=AlertType.HIGH_THREAT_RATE)

        assert len(alerts) == 2

    def test_get_alerts_unacknowledged(self, manager):
        alert = asyncio.run(manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.HIGH, "1"))
        asyncio.run(manager.create_alert(AlertType.ANOMALY_SPIKE, AlertSeverity.LOW, "2"))

        manager.acknowledge_alert(alert.id)

        alerts = manager.get_alerts(acknowledged=False)

        assert len(alerts) == 1

    def test_get_stats(self, manager):
        asyncio.run(manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.HIGH, "1"))
        asyncio.run(manager.create_alert(AlertType.ANOMALY_SPIKE, AlertSeverity.MEDIUM, "2"))
        alert = asyncio.run(manager.create_alert(AlertType.API_FAILURE, AlertSeverity.LOW, "3"))
        manager.acknowledge_alert(alert.id)

        stats = manager.get_stats()

        assert stats["total_alerts"] == 3
        assert stats["acknowledged"] == 1
        assert stats["unacknowledged"] == 2

    async def test_check_system_resources_cpu(self, manager):
        alerts = await manager.check_system_resources(95.0, 50.0)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.SYSTEM_RESOURCE

    async def test_check_system_resources_memory(self, manager):
        alerts = await manager.check_system_resources(50.0, 95.0)

        assert len(alerts) == 1

    async def test_check_system_resources_both(self, manager):
        alerts = await manager.check_system_resources(95.0, 95.0)

        assert len(alerts) == 2

    def test_clear_alerts(self, manager):
        asyncio.run(manager.create_alert(AlertType.HIGH_THREAT_RATE, AlertSeverity.HIGH, "1"))
        asyncio.run(manager.create_alert(AlertType.ANOMALY_SPIKE, AlertSeverity.MEDIUM, "2"))

        manager.clear_alerts()

        assert len(manager.alerts) == 0

    def test_max_alerts_limit(self):
        small_manager = AlertManager()
        small_manager.max_alerts = 10

        for i in range(15):
            asyncio.run(small_manager.create_alert(
                AlertType.HIGH_THREAT_RATE,
                AlertSeverity.LOW,
                f"Alert {i}",
            ))

        assert len(small_manager.alerts) <= 10


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_values(self):
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertType:
    """Tests for AlertType enum."""

    def test_type_values(self):
        assert AlertType.HIGH_THREAT_RATE.value == "high_threat_rate"
        assert AlertType.ANOMALY_SPIKE.value == "anomaly_spike"
        assert AlertType.API_FAILURE.value == "api_failure"
        assert AlertType.GEMINI_QUOTA_EXHAUSTED.value == "gemini_quota_exhausted"
        assert AlertType.SYSTEM_RESOURCE.value == "system_resource"
