"""
Notification Configuration Manager.

Manages notification channel configurations with JSON persistence.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationConfig:
    """Main notification configuration."""

    enabled: bool = False
    default_channel: str = "email"
    channels: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_updated: str | None = None


class NotificationConfigManager:
    """Manages notification channel configurations."""

    def __init__(self, config_path: Path = Path("./data/notification_config.json")):
        self.config_path = config_path
        self.config = NotificationConfig()
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    data = json.load(f)
                self.config = NotificationConfig(
                    enabled=data.get("enabled", False),
                    default_channel=data.get("default_channel", "email"),
                    channels=data.get("channels", {}),
                    last_updated=data.get("last_updated"),
                )
                logger.info(
                    "Notification config loaded",
                    extra={"channels": list(self.config.channels.keys())},
                )
            else:
                logger.info("No notification config found, using defaults")
                self._save_config()
        except Exception as e:
            logger.error(
                "Failed to load notification config",
                extra={"error": str(e)},
            )

    def _save_config(self) -> None:
        """Save configuration to JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config.last_updated = datetime.now(UTC).isoformat()

            data = {
                "enabled": self.config.enabled,
                "default_channel": self.config.default_channel,
                "channels": self.config.channels,
                "last_updated": self.config.last_updated,
            }

            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info("Notification config saved")

        except Exception as e:
            logger.error(
                "Failed to save notification config",
                extra={"error": str(e)},
            )

    def get_config(self) -> NotificationConfig:
        """Get current configuration."""
        return self.config

    def update_channel(
        self,
        channel_name: str,
        enabled: bool,
        settings: dict[str, Any],
    ) -> None:
        """Update a specific channel configuration."""
        self.config.channels[channel_name] = {
            "enabled": enabled,
            "settings": settings,
        }
        self._save_config()
        logger.info(
            "Channel config updated",
            extra={"channel": channel_name, "enabled": enabled},
        )

    def get_channel_config(self, channel_name: str) -> dict[str, Any] | None:
        """Get configuration for a specific channel."""
        return self.config.channels.get(channel_name)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable notifications."""
        self.config.enabled = enabled
        self._save_config()

    def set_default_channel(self, channel_name: str) -> None:
        """Set the default notification channel."""
        if channel_name in self.config.channels:
            self.config.default_channel = channel_name
            self._save_config()

    def get_enabled_channels(self) -> list[str]:
        """Get list of enabled channel names."""
        return [
            name for name, config in self.config.channels.items() if config.get("enabled", False)
        ]

    def to_dict(self) -> dict[str, Any]:
        """Export configuration as dictionary (sanitized)."""
        sanitized_channels = {}
        for name, config in self.config.channels.items():
            sanitized_channels[name] = {
                "enabled": config.get("enabled", False),
                "settings": self._sanitize_settings(config.get("settings", {})),
            }

        return {
            "enabled": self.config.enabled,
            "default_channel": self.config.default_channel,
            "channels": sanitized_channels,
            "last_updated": self.config.last_updated,
        }

    def _sanitize_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive information from settings for display."""
        sensitive_keys = ["smtp_password", "api_key", "webhook_url", "token"]
        sanitized = settings.copy()

        for key in sensitive_keys:
            if key in sanitized and sanitized[key]:
                sanitized[key] = "***"

        return sanitized


notification_config = NotificationConfigManager()
