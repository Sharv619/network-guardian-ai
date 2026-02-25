from typing import Optional

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import os

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""

    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    GEMINI_API_KEY: str = Field("", description="Google Gemini API Key")
    NOTION_TOKEN: Optional[str] = Field(None, description="Notion API Token (optional)")
    NOTION_DATABASE_ID: Optional[str] = Field(None, description="Notion Database ID (optional)")

    # AdGuard is now optional
    ADGUARD_URL: Optional[str] = Field(None, description="AdGuard Home URL")
    ADGUARD_USER: Optional[str] = Field(None, description="AdGuard Home Username")
    ADGUARD_PASS: Optional[str] = Field(None, description="AdGuard Home Password")

    POLL_INTERVAL: int = Field(30, ge=5, description="Polling interval in seconds")
    GOOGLE_SHEETS_CREDENTIALS: str = Field(
        "", description="Google Sheets Service Account Credentials (JSON)"
    )
    GOOGLE_SHEET_ID: str = Field("", description="Google Sheet ID for logging")

    # CORS configuration
    ALLOWED_ORIGINS: str = Field(
        "http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Database configuration
    DATABASE_URL: str = Field(
        "sqlite+aiosqlite:///./network_guardian.db", description="Database connection URL"
    )
    DATABASE_ECHO: bool = Field(False, description="Enable SQL query logging")
    DATABASE_POOL_SIZE: int = Field(5, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(10, description="Database maximum overflow connections")

    # Gemini model configuration
    GEMINI_CONFIRMED_MODELS: list[str] = Field(
        ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        description="Confirmed Gemini models for analysis",
    )

    # Gemini model configuration
    GEMINI_CONFIRMED_MODELS: list[str] = Field(
        ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        description="Confirmed Gemini models for analysis",
    )

    # Gemini model configuration
    GEMINI_CONFIRMED_MODELS: list[str] = Field(
        ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        description="Confirmed Gemini models for analysis",
    )

    # Security configuration
    ENABLE_SECURITY_HEADERS: bool = Field(True, description="Enable security headers middleware")
    ENABLE_HTTPS_REDIRECT: bool = Field(False, description="Enable HTTPS redirect middleware")

    # Backup configuration
    BACKUP_PATH: str = Field("./backups", description="Path for database backups")
    BACKUP_RETENTION_DAYS: int = Field(7, description="Days to retain backup files")
    BACKUP_ENABLED: bool = Field(True, description="Enable automatic backups")

    @property
    def is_valid(self) -> bool:
        """Check if minimum required configuration is present."""
        return (
            bool(self.GEMINI_API_KEY)
            and bool(self.GOOGLE_SHEETS_CREDENTIALS)
            and bool(self.GOOGLE_SHEET_ID)
        )

    @property
    def has_adguard(self) -> bool:
        """Check if AdGuard is fully configured."""
        return all([self.ADGUARD_URL, self.ADGUARD_USER, self.ADGUARD_PASS])

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


try:
    settings = Settings()  # type: ignore
    logger.info("Configuration loaded successfully")
except ValidationError as e:
    logger.critical(f"Configuration validation failed: {e}")
    raise ConfigurationError(f"Missing required environment variables: {e}")
