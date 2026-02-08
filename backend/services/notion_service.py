
from notion_client import Client
from typing import List
from ..core.config import settings
from ..api.models import ThreatEntry

notion = Client(auth=settings.NOTION_TOKEN)

def push_threat(domain: str, analysis: dict):
    if not settings.NOTION_DATABASE_ID:
        return
    try:
        notion.pages.create(
            parent={"database_id": settings.NOTION_DATABASE_ID},
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

def fetch_history() -> List[ThreatEntry]:
    if not settings.NOTION_DATABASE_ID:
        return []
    
    history = []
    try:
        response = notion.databases.query(database_id=settings.NOTION_DATABASE_ID, page_size=20)
        for page in response.get('results', []):
            props = page.get('properties', {})
            
            # Safe extraction helpers
            domain_prop = props.get('Domain', {}).get('title', [])
            domain = domain_prop[0].get('text', {}).get('content', 'Unknown') if domain_prop else 'Unknown'
            
            risk_prop = props.get('Risk', {}).get('select')
            risk = risk_prop.get('name', 'Unknown') if risk_prop else 'Unknown'
            
            cats = props.get('Category', {}).get('multi_select', [])
            category = cats[0].get('name', 'Unknown') if cats else 'Unknown'
            
            summary_prop = props.get('AI Insights', {}).get('rich_text', [])
            summary = summary_prop[0].get('text', {}).get('content', '') if summary_prop else ''
            
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
