#!/usr/bin/env python3
"""
Network Guardian AI - MCP Server

Model Context Protocol server that exposes Network Guardian AI's threat detection
and analysis capabilities to AI assistants and MCP clients.

Usage:
    1. Install dependencies: pip install -r backend/requirements.txt
    2. Run: python mcp_server.py
    3. Connect from your MCP client (Claude Desktop, etc.)

Configuration:
    Set up your MCP client to connect to this server using stdio transport.
    See MCP_INTEGRATION.md for detailed setup instructions.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from mcp.server.fastmcp import FastMCP

# Import Network Guardian components
from backend.core.config import settings
from backend.logic.analysis_cache import analysis_cache
from backend.logic.vector_store import vector_memory
from backend.logic.metadata_classifier import classifier
from backend.logic.ml_heuristics import calculate_entropy, calculate_digit_ratio, calculate_vowel_ratio
from backend.logic.anomaly_engine import AnomalyEngine
from backend.db.repository import get_domain_repository
from backend.services.sheets_logger import log_threat_to_sheet
from backend.services.gemini_analyzer import GeminiAnalyzer

# Initialize MCP server
mcp = FastMCP(
    name="network-guardian-ai",
    instructions="""
    Network Guardian AI - Autonomous Network Threat Intelligence System
    
    This server provides tools to:
    - Analyze domains for security threats using ML and AI
    - Retrieve recent threat detections and statistics
    - Access system health and configuration
    - Search for similar threats using vector similarity
    - Sync threat data to Google Sheets
    
    The system uses a multi-layered approach:
    1. Shannon Entropy analysis (local)
    2. Isolation Forest anomaly detection (ML)
    3. Metadata pattern matching (learned)
    4. Gemini AI semantic analysis (cloud)
    """
)


@mcp.tool()
async def analyze_domain(domain: str, full_analysis: bool = False) -> Dict[str, Any]:
    """
    Analyze a domain for security threats using the Network Guardian pipeline.
    
    Performs multi-layered analysis:
    - Layer 1: Shannon Entropy (detects DGA/random domains)
    - Layer 2: Feature analysis (digit ratio, vowel ratio, length)
    - Layer 3: Anomaly detection (Isolation Forest)
    - Layer 4: Metadata classification (pattern matching)
    - Layer 5: Gemini AI analysis (if full_analysis=True)
    
    Args:
        domain: The domain name to analyze (e.g., 'example.com')
        full_analysis: If True, includes Gemini AI analysis (default: False)
    
    Returns:
        Comprehensive analysis result including:
        - domain: The analyzed domain
        - risk_score: 0-100 risk assessment
        - category: Classification (Safe, Tracker, Malware, etc.)
        - entropy: Shannon entropy score
        - is_suspicious: Boolean flag for suspicious domains
        - anomaly_score: Isolation Forest score (if available)
        - confidence: Confidence level (0-1)
        - analysis_method: Which layer provided the result
        - gemini_analysis: AI analysis (if full_analysis=True)
    
    Example:
        >>> await analyze_domain("google-analytics.com")
        {
            "domain": "google-analytics.com",
            "risk_score": 45,
            "category": "Tracker",
            "entropy": 3.2,
            "is_suspicious": False,
            ...
        }
    """
    result = {
        "domain": domain,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "analysis_layers": {}
    }
    
    try:
        # Layer 1: Check cache first
        cached = analysis_cache.get(domain)
        if cached:
            result["cached"] = True
            result["cache_data"] = cached
            return result
        
        result["cached"] = False
        
        # Layer 2: Calculate entropy
        entropy = calculate_entropy(domain)
        result["analysis_layers"]["entropy"] = {
            "score": entropy,
            "is_suspicious": entropy > 4.0,
            "threshold": 4.0
        }
        
        # Layer 3: Calculate additional features
        digit_ratio = calculate_digit_ratio(domain)
        vowel_ratio = calculate_vowel_ratio(domain)
        result["analysis_layers"]["features"] = {
            "digit_ratio": digit_ratio,
            "vowel_ratio": vowel_ratio,
            "length": len(domain)
        }
        
        # Layer 4: Anomaly detection
        try:
            anomaly_engine = AnomalyEngine()
            anomaly_score = anomaly_engine.predict([domain])
            result["analysis_layers"]["anomaly"] = {
                "score": anomaly_score,
                "is_anomalous": anomaly_score < -0.1 if anomaly_score else False
            }
        except Exception as e:
            result["analysis_layers"]["anomaly"] = {"error": str(e)}
        
        # Layer 5: Metadata classification
        metadata = {"reason": "Unknown", "filter_id": None, "rule": None, "client": None}
        classification = classifier.classify(metadata)
        result["analysis_layers"]["metadata_classification"] = {
            "category": classification.category,
            "confidence": classification.confidence,
            "source": classification.source
        }
        
        # Determine overall risk
        risk_score = 0
        if entropy > 4.0:
            risk_score += 40
        if digit_ratio > 0.3:
            risk_score += 20
        if anomaly_score and anomaly_score < -0.1:
            risk_score += 30
        
        result["risk_score"] = min(risk_score, 100)
        result["category"] = classification.category
        result["is_suspicious"] = risk_score > 50
        result["confidence"] = classification.confidence
        result["analysis_method"] = "local_heuristics"
        
        # Layer 6: Optional Gemini AI analysis
        if full_analysis:
            try:
                analyzer = GeminiAnalyzer()
                gemini_result = await analyzer.analyze_domain(domain)
                result["gemini_analysis"] = gemini_result
                result["analysis_method"] = "gemini_ai"
                
                # Update risk score from Gemini if higher
                if gemini_result.get("risk_score", 0) > risk_score:
                    result["risk_score"] = gemini_result["risk_score"]
                    result["category"] = gemini_result.get("category", result["category"])
            except Exception as e:
                result["gemini_analysis"] = {"error": f"Gemini analysis failed: {str(e)}"}
        
        # Cache the result
        analysis_cache.set(domain, result)
        
        return result
        
    except Exception as e:
        return {
            "domain": domain,
            "error": str(e),
            "risk_score": 50,
            "category": "Unknown",
            "is_suspicious": True
        }


@mcp.tool()
async def get_recent_threats(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieve recently detected threats from the database.
    
    Fetches the most recent domain analyses from the system,
    including risk scores, categories, and timestamps.
    
    Args:
        limit: Maximum number of threats to return (default: 20, max: 100)
    
    Returns:
        List of recent threat detections with:
        - domain: The domain name
        - risk_score: Risk assessment (0-100)
        - category: Classification category
        - created_at: Detection timestamp
        - analysis_summary: Brief description
    
    Example:
        >>> await get_recent_threats(limit=5)
        [
            {
                "domain": "suspicious-tracker.com",
                "risk_score": 75,
                "category": "Tracker",
                "created_at": "2026-02-26T10:30:00Z",
                ...
            },
            ...
        ]
    """
    try:
        limit = min(limit, 100)  # Cap at 100
        repo = await get_domain_repository()
        domains = await repo.get_recent_domains(limit=limit)
        return [domain.to_dict() for domain in domains]
    except Exception as e:
        return [{"error": str(e), "domain": None}]


@mcp.tool()
async def get_threat_stats() -> Dict[str, Any]:
    """
    Get comprehensive threat statistics and system metrics.
    
    Returns:
        Statistics including:
        - total_threats: Total number of detected threats
        - risk_distribution: Breakdown by risk level
        - category_breakdown: Breakdown by threat category
        - recent_trend: Threat detection trend (last 24h)
        - cache_stats: Analysis cache performance
        - vector_store_stats: Vector memory statistics
    
    Example:
        >>> await get_threat_stats()
        {
            "total_threats": 1250,
            "risk_distribution": {"low": 800, "medium": 300, "high": 150},
            "category_breakdown": {"Tracker": 500, "Advertising": 400, ...},
            ...
        }
    """
    try:
        from backend.api.stats import get_stats as api_get_stats
        return api_get_stats()
    except Exception as e:
        return {"error": str(e), "total_threats": 0}


@mcp.tool()
async def get_system_status() -> Dict[str, Any]:
    """
    Check system health, configuration, and component status.
    
    Returns:
        Comprehensive system status including:
        - analysis_cache: Cache hit/miss statistics
        - vector_store: Vector memory stats
        - config: Configuration status (API keys, integrations)
        - database: Database connection status
        - components: Status of all system components
    
    Example:
        >>> await get_system_status()
        {
            "analysis_cache": {"hits": 1500, "misses": 200, ...},
            "vector_store": {"memories": 500, ...},
            "config": {"has_adguard": true, "gemini_available": true, ...},
            ...
        }
    """
    try:
        status = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "analysis_cache": analysis_cache.get_stats(),
            "vector_store": vector_memory.get_memory_stats(),
            "config": {
                "has_adguard": settings.has_adguard,
                "adguard_url": settings.ADGUARD_URL if settings.ADGUARD_URL else "not configured",
                "gemini_available": bool(settings.GEMINI_API_KEY),
                "google_sheets_available": bool(settings.GOOGLE_SHEET_ID),
                "notion_available": bool(settings.NOTION_TOKEN and settings.NOTION_DATABASE_ID)
            },
            "poll_interval": settings.POLL_INTERVAL,
            "is_valid_config": settings.is_valid
        }
        return status
    except Exception as e:
        return {"error": str(e), "status": "unhealthy"}


@mcp.tool()
async def get_config() -> Dict[str, Any]:
    """
    Retrieve system configuration (sensitive data redacted).
    
    Returns:
        Configuration including:
        - poll_interval: AdGuard polling frequency
        - integration_status: Status of external integrations
        - allowed_origins: CORS configuration
        - feature_flags: Enabled features
    
    Note: API keys and credentials are never exposed.
    """
    try:
        return {
            "poll_interval": settings.POLL_INTERVAL,
            "has_adguard": settings.has_adguard,
            "adguard_url": settings.ADGUARD_URL if settings.ADGUARD_URL else "not configured",
            "gemini_available": bool(settings.GEMINI_API_KEY),
            "google_sheets_available": bool(settings.GOOGLE_SHEET_ID),
            "notion_available": bool(settings.NOTION_TOKEN and settings.NOTION_DATABASE_ID),
            "allowed_origins": settings.allowed_origins_list,
            "is_valid_config": settings.is_valid
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def find_similar_threats(domain: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar threats using vector similarity search.
    
    Uses the vector store to find domains with similar characteristics
    based on embedding similarity. Useful for identifying related threats
    or campaign patterns.
    
    Args:
        domain: The domain to find similar threats for
        limit: Maximum number of similar threats to return (default: 5)
    
    Returns:
        List of similar domains with:
        - domain: The similar domain
        - similarity_score: Cosine similarity (0-1)
        - category: Classification category
        - risk_score: Risk assessment
    
    Example:
        >>> await find_similar_threats("malware-domain.com")
        [
            {
                "domain": "malicious-site.com",
                "similarity_score": 0.85,
                "category": "Malware",
                "risk_score": 85
            },
            ...
        ]
    """
    try:
        limit = min(limit, 20)
        results = vector_memory.query_memory(domain, k=limit)
        return results
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def get_threat_cluster(domain: str) -> List[Dict[str, Any]]:
    """
    Get threat cluster information for a domain.
    
    Retrieves all domains in the same threat cluster, useful for
    identifying coordinated campaigns or related infrastructure.
    
    Args:
        domain: The domain to analyze
    
    Returns:
        List of domains in the same cluster with metadata
    """
    try:
        results = vector_memory.get_threat_cluster(domain)
        return [match.to_dict() for match in results]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def get_entropy_analysis(domain: str) -> Dict[str, Any]:
    """
    Get Shannon entropy analysis for a domain.
    
    Shannon entropy measures the randomness of a domain name.
    High entropy (>4.0) often indicates DGA (Domain Generation Algorithm)
    or randomly generated domains, which are commonly used by malware.
    
    Args:
        domain: The domain to analyze
    
    Returns:
        Entropy analysis including:
        - entropy: Shannon entropy score (base 2)
        - is_suspicious: Whether entropy exceeds threshold
        - threshold: The threshold used (4.0)
        - interpretation: Human-readable explanation
    
    Example:
        >>> await get_entropy_analysis("x7k9m2p4.com")
        {
            "domain": "x7k9m2p4.com",
            "entropy": 4.2,
            "is_suspicious": true,
            "threshold": 4.0,
            "interpretation": "High entropy suggests random generation"
        }
    """
    try:
        entropy = calculate_entropy(domain)
        threshold = 4.0
        is_suspicious = entropy > threshold
        
        interpretation = "Normal entropy"
        if entropy > 4.5:
            interpretation = "Very high entropy - likely DGA or random generation"
        elif entropy > 4.0:
            interpretation = "High entropy - potentially suspicious"
        elif entropy < 2.0:
            interpretation = "Very low entropy - simple pattern"
        
        return {
            "domain": domain,
            "entropy": round(entropy, 4),
            "is_suspicious": is_suspicious,
            "threshold": threshold,
            "interpretation": interpretation
        }
    except Exception as e:
        return {"error": str(e), "domain": domain}


@mcp.tool()
async def sync_to_google_sheets(domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Manually trigger Google Sheets synchronization.
    
    Syncs threat data to Google Sheets for persistence and audit trail.
    Can sync a specific domain or all recent threats.
    
    Args:
        domain: Optional specific domain to sync (syncs all recent if None)
    
    Returns:
        Synchronization result including:
        - status: success/error
        - total_synced: Number of records synced
        - results: Individual sync results
    
    Note: Requires GOOGLE_SHEET_ID and GOOGLE_SHEETS_CREDENTIALS to be configured.
    """
    try:
        if not settings.GOOGLE_SHEET_ID:
            return {"error": "Google Sheets not configured", "status": "error"}
        
        if domain:
            # Sync specific domain
            # First analyze if not in database
            repo = await get_domain_repository()
            domain_obj = await repo.get_by_domain(domain)
            
            if not domain_obj:
                # Analyze first
                analysis = await analyze_domain(domain, full_analysis=True)
                # Create domain object (simplified)
                return {
                    "status": "success",
                    "domain": domain,
                    "analysis": analysis,
                    "note": "Domain analyzed but not persisted to database"
                }
            
            # Log to sheets
            result = await log_threat_to_sheet(domain_obj)
            return {"status": "success", "domain": domain, "result": result}
        else:
            # Sync all recent threats
            repo = await get_domain_repository()
            domains = await repo.get_recent_domains(limit=50)
            
            results = []
            for domain_obj in domains:
                try:
                    result = await log_threat_to_sheet(domain_obj)
                    results.append({
                        "domain": domain_obj.domain,
                        "success": True,
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "domain": domain_obj.domain,
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "status": "success",
                "total_synced": len([r for r in results if r["success"]]),
                "total_failed": len([r for r in results if not r["success"]]),
                "results": results
            }
    except Exception as e:
        return {"error": str(e), "status": "error"}


@mcp.tool()
async def get_knowledge_base_stats() -> Dict[str, Any]:
    """
    Get knowledge base and pattern learning statistics.
    
    Returns information about learned patterns, cached knowledge,
    and system intelligence metrics.
    
    Returns:
        Knowledge base statistics including:
        - pattern_count: Number of learned patterns
        - cache_entries: Number of cached analyses
        - vector_memories: Number of vector embeddings
        - learning_progress: System learning metrics
    """
    try:
        from backend.logic.knowledge_base import KnowledgeBase
        
        kb = KnowledgeBase()
        kb_stats = kb.get_stats() if hasattr(kb, 'get_stats') else {}
        
        return {
            "knowledge_base": kb_stats,
            "cache_stats": analysis_cache.get_stats(),
            "vector_store_stats": vector_memory.get_memory_stats(),
            "patterns_learned": kb_stats.get("patterns_count", 0) if kb_stats else 0
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def chat_with_system(message: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Chat with the Network Guardian AI system.
    
    Ask questions about:
    - Current threat landscape
    - System status and configuration
    - Specific domains or threats
    - Security recommendations
    
    Args:
        message: Your question or message
        context: Optional context about what you're asking about
    
    Returns:
        AI response with relevant information from the system
    """
    try:
        from backend.api.chat import chat as system_chat
        
        # Build context from system state
        system_context = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "config": await get_config(),
            "stats": await get_threat_stats()
        }
        
        if context:
            system_context["user_context"] = context
        
        response = await system_chat(message, context=system_context)
        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "response": f"I encountered an error: {str(e)}",
            "fallback": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


# Resource exposure (optional - for advanced MCP clients)
@mcp.resource("threats://recent")
async def get_recent_threats_resource() -> str:
    """Resource: Get recent threats as JSON"""
    threats = await get_recent_threats(limit=50)
    return json.dumps(threats, indent=2)


@mcp.resource("stats://current")
async def get_stats_resource() -> str:
    """Resource: Get current statistics as JSON"""
    stats = await get_threat_stats()
    return json.dumps(stats, indent=2)


@mcp.resource("status://system")
async def get_status_resource() -> str:
    """Resource: Get system status as JSON"""
    status = await get_system_status()
    return json.dumps(status, indent=2)


def main():
    """Start the MCP server"""
    # Load environment variables
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()
    
    print("=" * 60)
    print("Network Guardian AI - MCP Server")
    print("=" * 60)
    print()
    print("Available Tools:")
    print("  • analyze_domain - Analyze a domain for threats")
    print("  • get_recent_threats - Retrieve recent detected threats")
    print("  • get_threat_stats - Get threat statistics and trends")
    print("  • get_system_status - Check system health and status")
    print("  • get_config - Retrieve system configuration")
    print("  • find_similar_threats - Find similar threats using vector search")
    print("  • get_threat_cluster - Get threat cluster information")
    print("  • get_entropy_analysis - Get Shannon entropy analysis")
    print("  • sync_to_google_sheets - Manually trigger Google Sheets sync")
    print("  • get_knowledge_base_stats - Get knowledge base statistics")
    print("  • chat_with_system - Chat with the AI system")
    print()
    print("Resources:")
    print("  • threats://recent - Recent threats stream")
    print("  • stats://current - Current statistics")
    print("  • status://system - System status")
    print()
    print("Configuration Status:")
    print(f"  • AdGuard: {'✓' if settings.has_adguard else '✗'}")
    print(f"  • Gemini AI: {'✓' if settings.GEMINI_API_KEY else '✗'}")
    print(f"  • Google Sheets: {'✓' if settings.GOOGLE_SHEET_ID else '✗'}")
    print(f"  • Notion: {'✓' if settings.NOTION_TOKEN else '✗'}")
    print()
    print("Server running. Press Ctrl+C to stop.")
    print("=" * 60)
    
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()
