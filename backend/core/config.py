import logging
import os

from dotenv import load_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

IS_VERCEL = os.getenv("VERCEL") == "1"
DEFAULT_DATABASE_URL = (
    "sqlite+aiosqlite:////tmp/network_guardian.db"
    if IS_VERCEL
    else "sqlite+aiosqlite:///./network_guardian.db"
)


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""

    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
    )

    GEMINI_API_KEY: str = Field("", description="Google Gemini API Key (deprecated, use Ollama)")
    NOTION_TOKEN: str | None = Field(None, description="Notion API Token (optional)")
    NOTION_DATABASE_ID: str | None = Field(None, description="Notion Database ID (optional)")

    # Ollama Configuration (Local LLM)
    OLLAMA_ENABLED: bool = Field(
        not IS_VERCEL, description="Enable Ollama for local embeddings and analysis"
    )
    OLLAMA_BASE_URL: str = Field("http://localhost:11434", description="Ollama API base URL")
    OLLAMA_MODEL: str = Field("nomic-embed-text", description="Ollama embedding model")
    OLLAMA_CHAT_MODEL: str = Field(
        "llama3.2:1b", description="Ollama chat model for domain analysis"
    )

    # Ollama live feed enhancement
    OLLAMA_LIVE_FEED_ENABLED: bool = Field(
        not IS_VERCEL, description="Enable Ollama AI enhancement in live feed polling"
    )
    OLLAMA_MAX_CONCURRENT: int = Field(
        2, ge=1, le=10, description="Max concurrent Ollama requests (prevents resource exhaustion)"
    )
    OLLAMA_CALL_COOLDOWN: float = Field(
        2.0, ge=0, description="Seconds between Ollama calls in poller"
    )

    # Embedding provider choice
    EMBEDDING_PROVIDER: str = Field(
        "mock" if IS_VERCEL else "ollama",
        description="Provider: ollama (local), sentence-transformers, or mock",
    )

    # AdGuard is now optional
    ADGUARD_URL: str | None = Field(None, description="AdGuard Home URL")
    ADGUARD_USER: str | None = Field(None, description="AdGuard Home Username")
    ADGUARD_PASS: str | None = Field(None, description="AdGuard Home Password")

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
        DEFAULT_DATABASE_URL, description="Database connection URL"
    )
    DATABASE_ECHO: bool = Field(False, description="Enable SQL query logging")
    DATABASE_POOL_SIZE: int = Field(5, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(10, description="Database maximum overflow connections")

    # Security configuration
    JWT_SECRET_KEY: str = Field("", description="JWT Secret Key for token generation")
    ENABLE_SECURITY_HEADERS: bool = Field(True, description="Enable security headers middleware")
    ENABLE_HTTPS_REDIRECT: bool = Field(False, description="Enable HTTPS redirect middleware")

    # Stripe Billing Configuration
    STRIPE_API_KEY: str = Field("", description="Stripe API Key")
    STRIPE_WEBHOOK_SECRET: str = Field("", description="Stripe Webhook Secret")
    STRIPE_PRO_PRICE_ID: str = Field("", description="Stripe Price ID for Pro tier")
    STRIPE_ENTERPRISE_PRICE_ID: str = Field("", description="Stripe Price ID for Enterprise tier")

    # Backup configuration
    BACKUP_PATH: str = Field("./backups", description="Path for database backups")
    BACKUP_RETENTION_DAYS: int = Field(7, description="Days to retain backup files")
    BACKUP_ENABLED: bool = Field(not IS_VERCEL, description="Enable automatic backups")

    # Blocklist configuration
    BLOCKLIST_ENABLED: bool = Field(not IS_VERCEL, description="Enable blocklist knowledge base")
    BLOCKLIST_SYNC_INTERVAL: int = Field(
        21600, description="Blocklist sync interval in seconds (default: 6 hours)"
    )
    BLOCKLIST_SOURCES: str = Field(
        "adguard_dns,easylist,easyprivacy,steven_black",
        description="Comma-separated list of blocklist sources to sync",
    )
    BLOCKLIST_AUTO_SYNC: bool = Field(True, description="Auto-sync blocklists on startup if empty")

    @property
    def is_valid(self) -> bool:
        """Check if minimum required configuration is present."""
        return bool(self.GOOGLE_SHEETS_CREDENTIALS) and bool(self.GOOGLE_SHEET_ID)

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
    raise ConfigurationError(f"Missing required environment variables: {e}") from e
