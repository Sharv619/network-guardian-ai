
import os
import json
import gspread
from google.oauth2.service_account import Credentials

_client = None

def get_sheets_service():
    """
    SRE Pattern: Singleton Client to prevent Quota Exceeded (429) errors.
    """
    global _client
    if _client:
        return _client

    raw_creds = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not raw_creds:
        return None

    # SRE Pattern: Sanitize & Validate input strings
    creds_json = raw_creds.strip().strip("'").strip('"')
    print(f"DEBUG: Credentials string length: {len(creds_json)}")

    if not creds_json.startswith("{"):
        print("⚠️ Config Error: GOOGLE_SHEETS_CREDENTIALS is not a valid JSON object. Check your .env file.")
        return None

    try:
        # Parse the JSON string from .env
        creds_dict = json.loads(creds_json)
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        _client = client
        return client
    except json.JSONDecodeError as je:
        print(f"⚠️ Auth Error: GOOGLE_SHEETS_CREDENTIALS is malformed JSON. {je}")
        return None
    except Exception as e:
        print(f"⚠️ Auth Error: Could not parse Google Credentials. {e}")
        return None

def log_threat_to_sheet(domain: str, analysis: dict):
    """
    Logs threat data to Google Sheet defined in ENV 'GOOGLE_SHEET_ID'.
    """
    client = get_sheets_service()
    if not client: 
        return

    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        print("⚠️ Config Error: GOOGLE_SHEET_ID missing from .env")
        return

    try:
        sheet = client.open_by_key(spreadsheet_id).sheet1
        
        # Prepare row data
        row = [
            analysis.get('timestamp', 'Now'),
            domain,
            analysis.get('risk_score', 'Unknown'),
            analysis.get('category', 'Unknown'),
            analysis.get('summary', '')
        ]
        
        sheet.append_row(row)
        print(f"📊 Logged to Sheets: {domain}")
    except Exception as e:
        print(f"Sheets API Error: {e}")

import time

_client = None
_history_cache = None
_last_fetch_time = 0
CACHE_TTL = 30 # seconds

def fetch_recent_from_sheets(limit=20):
    """
    Fetches the last N rows from the Google Sheet.
    Includes a TTL cache to avoid Google API Quota limits (429).
    """
    global _history_cache, _last_fetch_time
    
    now = time.time()
    if _history_cache is not None and (now - _last_fetch_time) < CACHE_TTL:
        return _history_cache

    client = get_sheets_service()
    if not client: return []

    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id: return []

    try:
        sheet = client.open_by_key(spreadsheet_id).sheet1
        all_values = sheet.get_all_values()
        
        if len(all_values) > 1:
            rows = all_values[1:] # Skip header
            recent_rows = rows[-limit:]
            recent_rows.reverse() # Newest first
            
            # Map back to ThreatEntry dict
            history = []
            for r in recent_rows:
                if len(r) >= 5:
                    history.append({
                        "timestamp": r[0],
                        "domain": r[1],
                        "risk_score": r[2],
                        "category": r[3],
                        "summary": r[4]
                    })
            
            _history_cache = history
            _last_fetch_time = now
            return history
        else:
            print("DEBUG: Sheet is empty, nothing to show in Live Feed.")
            _history_cache = []
            _last_fetch_time = now
            
        return []
    except Exception as e:
        print(f"Sheets Fetch Error: {e}")
        return _history_cache if _history_cache else []
