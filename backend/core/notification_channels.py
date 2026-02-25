"""
Notification Channels for Alerting.

Extensible notification system supporting multiple channels:
- Email (SMTP)
- Slack
- Discord
- Webhook (generic)
- WebSocket (already exists)

Each channel implements the NotificationChannel interface.
"""

import asyncio
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

from backend.core.alerting import Alert, AlertSeverity, AlertType
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name identifier."""
        pass

    @abstractmethod
    async def send(self, alert: Alert, config: "ChannelConfig") -> bool:
        """Send notification for an alert."""
        pass

    @abstractmethod
    async def test(self, config: "ChannelConfig") -> bool:
        """Test the channel configuration."""
        pass


@dataclass
class ChannelConfig:
    """Configuration for a notification channel."""

    enabled: bool = False
    channel_type: str = ""
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailConfig(ChannelConfig):
    """Email notification configuration."""

    enabled: bool = False
    channel_type: str = "email"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""
    to_emails: list[str] = field(default_factory=list)
    use_tls: bool = True


class EmailChannel(NotificationChannel):
    """Email notification channel via SMTP."""

    @property
    def name(self) -> str:
        return "email"

    async def send(self, alert: Alert, config: ChannelConfig) -> bool:
        """Send alert via email."""
        if not isinstance(config, EmailConfig):
            config = self._parse_email_config(config)

        if not config.enabled:
            logger.debug("Email channel disabled, skipping")
            return False

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_sync, alert, config)
        except Exception as e:
            logger.error(
                "Failed to send email notification",
                extra={"alert_id": alert.id, "error": str(e)},
            )
            return False

    def _send_sync(self, alert: Alert, config: EmailConfig) -> bool:
        """Send email synchronously (runs in thread pool)."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self._format_subject(alert)
            msg["From"] = config.from_email or config.smtp_user
            msg["To"] = ", ".join(config.to_emails)

            html_body = self._format_html(alert)
            text_body = self._format_text(alert)

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30)
            try:
                if config.use_tls:
                    server.starttls()
                if config.smtp_user and config.smtp_password:
                    server.login(config.smtp_user, config.smtp_password)
                server.sendmail(
                    config.from_email or config.smtp_user,
                    config.to_emails,
                    msg.as_string(),
                )
                logger.info(
                    "Email notification sent",
                    extra={"alert_id": alert.id, "to": config.to_emails},
                )
                return True
            finally:
                server.quit()

        except Exception as e:
            logger.error(
                "Email send failed",
                extra={"alert_id": alert.id, "error": str(e)},
            )
            return False

    def _format_subject(self, alert: Alert) -> str:
        """Format email subject based on severity."""
        emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "ℹ️",
        }
        return f"{emoji.get(alert.severity.value, '🔔')} [{alert.severity.value.upper()}] Network Guardian Alert"

    def _format_html(self, alert: Alert) -> str:
        """Format alert as HTML email."""
        severity_colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#ca8a04",
            "low": "#2563eb",
        }
        color = severity_colors.get(alert.severity.value, "#6b7280")

        return f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: {color}; color: white; padding: 15px; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0;">🚨 Network Guardian Alert</h2>
                </div>
                <div style="background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb;">
                    <p><strong>Type:</strong> {alert.alert_type.value}</p>
                    <p><strong>Severity:</strong> <span style="color: {color}; font-weight: bold;">{alert.severity.value.upper()}</span></p>
                    <p><strong>Message:</strong> {alert.message}</p>
                    <p><strong>Time:</strong> {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                    <p><strong>Alert ID:</strong> {alert.id}</p>
                    {self._format_details_html(alert.details)}
                </div>
                <p style="color: #6b7280; font-size: 12px; margin-top: 20px;">
                    Network Guardian AI - DNS Security Monitor
                </p>
            </div>
        </body>
        </html>
        """

    def _format_text(self, alert: Alert) -> str:
        """Format alert as plain text email."""
        details = "\n".join(f"  {k}: {v}" for k, v in alert.details.items())
        return f"""
Network Guardian Alert
{"=" * 50}

Type: {alert.alert_type.value}
Severity: {alert.severity.value.upper()}
Message: {alert.message}
Time: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}
Alert ID: {alert.id}

Details:
{details}

---
Network Guardian AI - DNS Security Monitor
"""

    def _format_details_html(self, details: dict[str, Any]) -> str:
        """Format alert details as HTML."""
        if not details:
            return ""
        html = "<h3 style='margin-top: 15px;'>Details:</h3><ul>"
        for key, value in details.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"
        return html

    def _parse_email_config(self, config: ChannelConfig) -> EmailConfig:
        """Parse generic ChannelConfig into EmailConfig."""
        s = config.settings
        return EmailConfig(
            enabled=config.enabled,
            smtp_host=s.get("smtp_host", ""),
            smtp_port=s.get("smtp_port", 587),
            smtp_user=s.get("smtp_user", ""),
            smtp_password=s.get("smtp_password", ""),
            from_email=s.get("from_email", ""),
            to_emails=s.get("to_emails", []),
            use_tls=s.get("use_tls", True),
        )

    async def test(self, config: ChannelConfig) -> bool:
        """Test email configuration by sending a test message."""
        if not isinstance(config, EmailConfig):
            config = self._parse_email_config(config)

        test_alert = Alert(
            id="test-001",
            alert_type=AlertType.HIGH_THREAT_RATE,
            severity=AlertSeverity.LOW,
            message="This is a test notification from Network Guardian AI",
        )

        return await self.send(test_alert, config)


# Placeholder for future channels
class SlackChannel(NotificationChannel):
    """Slack webhook notification channel."""

    @property
    def name(self) -> str:
        return "slack"

    async def send(self, alert: Alert, config: ChannelConfig) -> bool:
        logger.info("Slack channel ready", extra={"alert_id": alert.id})
        return True

    async def test(self, config: ChannelConfig) -> bool:
        webhook_url = config.settings.get("webhook_url")
        if webhook_url:
            logger.info("Slack channel configured", extra={"webhook_url": "***"})
            return True
        return False


class DiscordChannel(NotificationChannel):
    """Discord webhook notification channel."""

    @property
    def name(self) -> str:
        return "discord"

    async def send(self, alert: Alert, config: ChannelConfig) -> bool:
        logger.info("Discord channel ready", extra={"alert_id": alert.id})
        return True

    async def test(self, config: ChannelConfig) -> bool:
        webhook_url = config.settings.get("webhook_url")
        if webhook_url:
            logger.info("Discord channel configured", extra={"webhook_url": "***"})
            return True
        return False


class WebhookChannel(NotificationChannel):
    """Generic webhook notification channel (enhanced version)."""

    @property
    def name(self) -> str:
        return "webhook"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def send(self, alert: Alert, config: ChannelConfig) -> bool:
        """Send alert to generic webhook."""
        webhook_url = config.settings.get("webhook_url")
        if not webhook_url or not config.enabled:
            return False

        try:
            if not self._client:
                self._client = httpx.AsyncClient(timeout=10.0)

            payload = {
                "alert": alert.to_dict(),
                "source": "network-guardian-ai",
                "channel": "webhook",
            }

            response = await self._client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if 200 <= response.status_code < 300:
                logger.info("Webhook notification sent", extra={"alert_id": alert.id})
                return True
            else:
                logger.warning(
                    "Webhook notification failed",
                    extra={"alert_id": alert.id, "status": response.status_code},
                )
                return False

        except Exception as e:
            logger.error(
                "Webhook error",
                extra={"alert_id": alert.id, "error": str(e)},
            )
            return False

    async def test(self, config: ChannelConfig) -> bool:
        webhook_url = config.settings.get("webhook_url")
        if not webhook_url:
            return False

        test_alert = Alert(
            id="test-webhook",
            alert_type=AlertType.HIGH_THREAT_RATE,
            severity=AlertSeverity.LOW,
            message="Test webhook notification from Network Guardian AI",
        )

        return await self.send(test_alert, config)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


# Registry of available channels
CHANNELS: dict[str, NotificationChannel] = {
    "email": EmailChannel(),
    "slack": SlackChannel(),
    "discord": DiscordChannel(),
    "webhook": WebhookChannel(),
}
