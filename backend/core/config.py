
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    
    # AdGuard is now optional
    ADGUARD_URL = os.getenv("ADGUARD_URL", "")
    ADGUARD_USER = os.getenv("ADGUARD_USER", "")
    ADGUARD_PASS = os.getenv("ADGUARD_PASS", "")
    
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  

    @property
    def is_valid(self) -> bool:
        # Minimum requirement is Gemini API Key
        return bool(self.GEMINI_API_KEY)
    
    @property
    def has_adguard(self) -> bool:
        return all([self.ADGUARD_URL, self.ADGUARD_USER, self.ADGUARD_PASS])

settings = Settings()
