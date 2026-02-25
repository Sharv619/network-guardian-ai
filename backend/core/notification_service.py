"""
Notification Service - Ties alerts to notification channels.

This service is called when alerts are created to send notifications
through configured channels.
"""

from typing import TYPE_CHECKING, Any

from backend.core.alerting import Alert, AlertManager, alert_manager
from backend.core.logging_config import get_logger
from backend.core.notification_channels import (
    CHANNELS,
    ChannelConfig,
    EmailConfig,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class NotificationService:
    """Service for sending notifications through configured channels."""

    def __init__(
        self,
        alert_manager: AlertManager,
        config_manager: Any | None = None,
    ) -> None:
        self.alert_manager = alert_manager
        self._config_manager: Any | None = config_manager

    def _get_config_manager(self) -> Any:
        """Lazy load config manager to avoid circular imports."""
        if self._config_manager is None:
            from backend.core.notification_config import notification_config

            self._config_manager = notification_config
        return self._config_manager

    async def send_alert_notification(self, alert: Alert) -> dict[str, bool]:
        """Send alert through all enabled notification channels."""
        results: dict[str, bool] = {}
        config = self._get_config_manager().get_config()

        if not config.enabled:
            logger.debug("Notifications disabled, skipping")
            return results

        enabled_channels = self._get_config_manager().get_enabled_channels()

        for channel_name in enabled_channels:
            channel = CHANNELS.get(channel_name)
            if not channel:
                logger.warning(f"Channel {channel_name} not found")
                continue

            channel_config_data = self._get_config_manager().get_channel_config(channel_name)
            if not channel_config_data:
                continue

            channel_config = self._build_channel_config(channel_name, channel_config_data)

            try:
                success = await channel.send(alert, channel_config)
                results[channel_name] = success

                if success:
                    logger.info(
                        f"Notification sent via {channel_name}",
                        extra={"alert_id": alert.id},
                    )
                else:
                    logger.warning(
                        f"Notification failed via {channel_name}",
                        extra={"alert_id": alert.id},
                    )

            except Exception as e:
                logger.error(
                    f"Error sending notification via {channel_name}",
                    extra={"alert_id": alert.id, "error": str(e)},
                )
                results[channel_name] = False

        return results

    def _build_channel_config(
        self, channel_name: str, config_data: dict[str, Any]
    ) -> ChannelConfig:
        """Build channel config from stored data."""
        enabled = config_data.get("enabled", False)
        settings = config_data.get("settings", {})

        if channel_name == "email":
            return EmailConfig(
                enabled=enabled,
                channel_type="email",
                smtp_host=settings.get("smtp_host", ""),
                smtp_port=settings.get("smtp_port", 587),
                smtp_user=settings.get("smtp_user", ""),
                smtp_password=settings.get("smtp_password", ""),
                from_email=settings.get("from_email", ""),
                to_emails=settings.get("to_emails", []),
                use_tls=settings.get("use_tls", True),
            )

        return ChannelConfig(
            enabled=enabled,
            channel_type=channel_name,
            settings=settings,
        )

    async def test_channel(self, channel_name: str) -> dict[str, Any]:
        """Test a specific notification channel."""
        channel = CHANNELS.get(channel_name)
        if not channel:
            return {"success": False, "message": f"Channel {channel_name} not found"}

        channel_config_data = self._get_config_manager().get_channel_config(channel_name)
        if not channel_config_data:
            return {"success": False, "message": "Channel not configured"}

        channel_config = self._build_channel_config(channel_name, channel_config_data)

        try:
            success = await channel.test(channel_config)
            return {
                "success": success,
                "message": f"Test {'successful' if success else 'failed'} via {channel_name}",
            }
        except Exception as e:
            logger.error(
                "Channel test failed",
                extra={"channel": channel_name, "error": str(e)},
            )
            return {"success": False, "message": f"Test error: {str(e)}"}


notification_service = NotificationService(alert_manager)
