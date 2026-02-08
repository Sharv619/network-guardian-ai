
import time
import requests
from ..core.config import settings
from .gemini_analyzer import analyze_domain
from .notion_service import push_threat
from .sheets_logger import log_threat_to_sheet
from ..logic.ml_heuristics import calculate_entropy
from ..core.state import automated_threats

# In-memory deduplication set
processed_domains = set()

def poll_adguard():
    print("Starting AdGuard Poller...")
    
    # SRE Pattern: Use persistent sessions for repeated polling
    session = requests.Session()
    session.auth = (settings.ADGUARD_USER, settings.ADGUARD_PASS)
    session.headers.update({"Accept": "application/json"})

    while True:
        try:
            # SRE Pattern: Use Env Var with fallback to internal DNS
            url = f"{settings.ADGUARD_URL}/control/querylog" if settings.ADGUARD_URL else "http://adguard:3000/control/querylog"
            try:
                print(f"DEBUG: Polling AdGuard at {url}...")
                r = session.get(url, timeout=10)
                print(f"DEBUG: AdGuard Status: {r.status_code}")
                
                if r.status_code == 401:
                    print("CRITICAL: AdGuard Authentication Failed. Check credentials in .env.")
                
                if r.status_code == 200:
                    content_type = r.headers.get('Content-Type', '')
                    try:
                        logs = r.json().get('data', [])
                    except ValueError:
                        print(f"AdGuard Response Error: Not JSON. Content-Type: {content_type}")
                        print(f"Response starts with: {r.text[:100]}")
                        time.sleep(settings.POLL_INTERVAL)
                        continue

                    # process logs
                    for log in logs:
                        domain = log.get('question', {}).get('name')
                        if not domain or domain.endswith('.local') or domain.endswith('.arpa'):
                            continue

                        if domain not in processed_domains:
                            print(f"Processing New Domain: {domain}")
                            
                            # --- Local ML Heuristic Check ---
                            entropy = calculate_entropy(domain)
                            analysis = None
                            
                            if entropy > 3.8:
                                print(f"High Entropy Detected ({entropy:.2f}). Skipping Gemini.")
                                analysis = {
                                    "risk_score": "High",
                                    "category": "Malware",
                                    "summary": f"High Entropy Domain ({entropy:.2f}). Likely DGA/C2.",
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                }
                            else:
                                try:
                                    print(f"Analyzing with Gemini: {domain}")
                                    analysis = analyze_domain(domain)
                                    analysis['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
                                except Exception as e:
                                    print(f"Gemini API Failed: {e}. Falling back to Heuristics.")
                                    analysis = {
                                        "risk_score": "Unknown",
                                        "category": "Unknown",
                                        "summary": f"Analysis failed. Entropy: {entropy:.2f}",
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                    }
                            
                            # Check for Privacy/Location Tracking
                            if any(kw in domain for kw in ['geo', 'location', 'gps', 'waa-pa']):
                                print(f"PRIVACY ALERT: Location Tracking Detected: {domain}")

                            # Log to Persistence Layer (Notion + Sheets)
                            push_threat(domain, analysis)
                            log_threat_to_sheet(domain, analysis) 
                            
                            # Update Live Memory (Automated Only)
                            automated_threats.insert(0, {
                                "domain": domain, 
                                "risk_score": analysis.get("risk_score"),
                                "category": analysis.get("category"),
                                "summary": analysis.get("summary"),
                                "timestamp": analysis.get("timestamp")
                            })
                            # Keep buffer small
                            if len(automated_threats) > 50:
                                automated_threats.pop()
                            
                            processed_domains.add(domain)
                            if len(processed_domains) > 5000:
                                processed_domains.clear()
                else:
                    print(f"AdGuard Poller Error: Status {r.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"AdGuard Connection Failed: {e}")
            
        except Exception as e:
            print(f"Poller Loop Error: {e}")
            
        time.sleep(settings.POLL_INTERVAL)
