
import os
import time
import json
import requests
import threading
import uvicorn
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from notion_client import Client
import google.generativeai as genai
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from google.generativeai.types import GenerationConfig

# Load environment variables
load_dotenv()

# --- Configuration & Initialization ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
ADGUARD_URL = os.getenv("ADGUARD_URL")
ADGUARD_USER = os.getenv("ADGUARD_USER")
ADGUARD_PASS = os.getenv("ADGUARD_PASS")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))

if not all([GEMINI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID]):
    # Raise an error to stop execution immediately if keys are missing
    raise ValueError("CRITICAL: Missing environment variables (GEMINI_API_KEY, NOTION_TOKEN, or NOTION_DATABASE_ID).")

# Initialize Clients
notion = Client(auth=NOTION_TOKEN)
# Set API key using environment variable approach
if GEMINI_API_KEY:
    os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY

# Use a flash model for speed
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    system_instruction="You are a cybersecurity expert. Analyze the domain. Return ONLY valid JSON."
)

# In-memory deduplication
processed_domains = set()

# --- Models ---
class AnalysisRequest(BaseModel):
    domain: str
    registrar: Optional[str] = None
    age: Optional[str] = None
    organization: Optional[str] = None

class ThreatEntry(BaseModel):
    domain: str
    risk_score: str
    category: str
    summary: str
    timestamp: str

# --- Core Logic ---

def analyze_domain_with_gemini(domain: str, context: Optional[Dict[str, Any]] = None) -> dict:
    context_str = f" Context: {context}" if context else ""
    prompt = f"""
    Analyze this domain for security risks: {domain}{context_str}
    
    Return a valid JSON object with these exact keys:
    {{
      "risk_score": "Low" | "Medium" | "High",
      "category": "Ad" | "Tracker" | "Malware" | "System" | "Unknown",
      "summary": "Concise 1-sentence explanation"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Robust JSON extraction using Regex
        import re
        match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
        if match:
            text = match.group(1)
            
        return json.loads(text)
    except Exception as e:
        print(f"Gemini Analysis Failed: {e}")
        return {
            "risk_score": "Unknown",
            "category": "Error",
            "summary": "AI analysis unavailable."
        }

def push_to_notion(domain: str, analysis: dict):
    if not NOTION_DATABASE_ID:
        return
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Domain": {"title": [{"text": {"content": domain}}]},
                "Risk": {"select": {"name": analysis.get('risk_score', 'Unknown')}},
                "Category": {"multi_select": [{"name": analysis.get('category', 'Unknown')}]},
                "AI Insights": {"rich_text": [{"text": {"content": analysis.get('summary', '')}}]}
            }
        )
        print(f"Logged to Notion: {domain}")
    except Exception as e:
        print(f"Notion Logging Failed: {e}")
def fetch_history_from_notion() -> List[ThreatEntry]:
    if not NOTION_DATABASE_ID:
        return []
    
    history = []
    try:
        response = notion.databases.query(database_id=NOTION_DATABASE_ID, page_size=20)
        for page in response.get('results', []):
            props = page.get('properties', {})
            
            # Safe extraction helpers
            domain = props.get('Domain', {}).get('title', [{}])[0].get('text', {}).get('content', 'Unknown') if props.get('Domain', {}).get('title') else 'Unknown'
            risk = props.get('Risk', {}).get('select', {}).get('name', 'Unknown') if props.get('Risk', {}).get('select') else 'Unknown'
            
            cats = props.get('Category', {}).get('multi_select', [])
            category = cats[0].get('name', 'Unknown') if cats else 'Unknown'
            
            summary = props.get('AI Insights', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '') if props.get('AI Insights', {}).get('rich_text') else ''
            
            history.append(ThreatEntry(
                domain=domain,
                risk_score=risk,
                category=category,
                summary=summary,
                timestamp=page.get('created_time', '')
            ))
    except Exception as e:
        print(f"History Fetch Error: {e}")
    return history

# --- Background Worker ---

def background_poller():
    print("Starting AdGuard Poller...")
    while True:
        try:
            if ADGUARD_URL and ADGUARD_USER and ADGUARD_PASS:
                url = f"{ADGUARD_URL}/control/querylog"
                try:
                    r = requests.get(url, auth=(ADGUARD_USER, ADGUARD_PASS), timeout=10)
                    if r.status_code == 200:
                        logs = r.json().get('data', [])
                        # ... process logs ...
                        for log in logs:
                            domain = log.get('question', {}).get('name')
                            if not domain or domain.endswith('.local') or domain.endswith('.arpa'):
                                continue

                            if domain not in processed_domains:
                                print(f"Processing New Domain: {domain}")
                                analysis = analyze_domain_with_gemini(domain)
                                push_to_notion(domain, analysis)
                                processed_domains.add(domain)
                                if len(processed_domains) > 5000:
                                    processed_domains.clear()
                    else:
                        print(f"AdGuard Poller Error: Status {r.status_code}")
                except requests.exceptions.RequestException as e:
                     print(f"AdGuard Connection Failed: {e}")
            
        except Exception as e:
            print(f"Poller Loop Error: {e}")
            
        time.sleep(POLL_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=background_poller, daemon=True)
    t.start()
    yield

# --- FastAPI Setup ---
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "processed_count": len(processed_domains)}

@app.post("/analyze")
def api_analyze(req: AnalysisRequest):
    """Manual analysis endpoint."""
    context = {}
    if req.registrar: context['Registrar'] = req.registrar
    if req.age: context['Age'] = req.age
    
    analysis = analyze_domain_with_gemini(req.domain, context)
    
    # Push manual scans to Notion too? Usually yes for history.
    push_to_notion(req.domain, analysis)
    
    return analysis

@app.get("/history", response_model=List[ThreatEntry])
def api_history():
    """Get recent threat history from Notion."""
    return fetch_history_from_notion()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
