
from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key")
    NOTION_TOKEN: Optional[str] = Field(None, description="Notion API Token (optional)")
    NOTION_DATABASE_ID: Optional[str] = Field(None, description="Notion Database ID (optional)")
    
    # AdGuard is now optional
    ADGUARD_URL: Optional[str] = Field(None, description="AdGuard Home URL")
    ADGUARD_USER: Optional[str] = Field(None, description="AdGuard Home Username")
    ADGUARD_PASS: Optional[str] = Field(None, description="AdGuard Home Password")
    
    POLL_INTERVAL: int = Field(30, ge=5, description="Polling interval in seconds")
    GOOGLE_SHEETS_CREDENTIALS: str = Field(..., description="Google Sheets Service Account Credentials (JSON)")
    GOOGLE_SHEET_ID: str = Field(..., description="Google Sheet ID for logging")

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def is_valid(self) -> bool:
        # Minimum requirement is Gemini API Key and Google Sheets credentials
        return bool(self.GEMINI_API_KEY) and bool(self.GOOGLE_SHEETS_CREDENTIALS) and bool(self.GOOGLE_SHEET_ID)
    
    @property
    def has_adguard(self) -> bool:
        return all([self.ADGUARD_URL, self.ADGUARD_USER, self.ADGUARD_PASS])

try:
    settings = Settings()
    logger.info("Configuration loaded successfully")
except ValidationError as e:
    logger.critical(f"Configuration validation failed: {e}")
    raise SystemExit(1)
