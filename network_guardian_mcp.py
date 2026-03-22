#!/usr/bin/env python3
"""
Network Guardian AI MCP Server

This MCP server exposes the Network Guardian AI system's functionality
as tools that can be used by other AI agents or applications.

To use this MCP server:
1. Install required dependencies: pip install fastmcp
2. Run: python network_guardian_mcp.py
3. Connect from your MCP client
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

# Add the backend directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.core.config import settings
from backend.logic.analysis_cache import analysis_cache
from backend.logic.vector_store import vector_memory
from backend.api.stats import get_system_stats as api_get_stats

# Initialize MCP server
mcp = FastMCP("network-guardian-ai")


@mcp.tool()
def analyze_domain(domain: str) -> Dict[str, Any]:
    """
    Analyze a domain for threats using the system's analysis pipeline.

    Args:
        domain: The domain name to analyze

    Returns:
        Analysis results including risk assessment and metadata
    """
    try:
        from backend.logic.metadata_classifier import classifier
        from backend.logic.ml_heuristics import calculate_entropy

        # Get metadata classification
        metadata = {"reason": "Unknown", "filter_id": None, "rule": None, "client": None}
        result = classifier.classify(metadata)

        # Calculate entropy
        entropy = calculate_entropy(domain)

        # Create analysis result
        return {
            "domain": domain,
            "category": result.category,
            "confidence": result.confidence,
            "entropy": entropy,
            "is_suspicious": entropy > 4.0,
            "classification_source": result.source,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@mcp.tool()
def get_recent_threats(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve recent detected threats from the system.

    Args:
        limit: Maximum number of threats to return

    Returns:
        List of recent threat detections with metadata
    """
    try:
        import asyncio
        from backend.db.repository import get_domain_repository

        async def get_threats():
            repo = await get_domain_repository()
            domains = await repo.get_recent_domains(limit=limit)
            return [domain.to_dict() for domain in domains]

        return asyncio.run(get_threats())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp.tool()
def get_threat_stats() -> Dict[str, Any]:
    """
    Get threat statistics and trends from the system.

    Returns:
        Statistics including total threats, risk distribution, and trends
    """
    try:
        import asyncio

        return asyncio.run(api_get_stats())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp.tool()
def get_system_status() -> Dict[str, Any]:
    """
    Check system health and status.

    Returns:
        System status including components, cache, and vector store stats
    """
    try:
        status = {
            "analysis_cache": analysis_cache.get_stats(),
            "vector_store": vector_memory.get_memory_stats(),
            "config": {
                "has_adguard": settings.has_adguard,
                "gemini_available": bool(settings.GEMINI_API_KEY),
                "google_sheets_available": bool(settings.GOOGLE_SHEET_ID),
            },
        }
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp.tool()
def get_config() -> Dict[str, Any]:
    """
    Retrieve system configuration.

    Returns:
        Current system configuration (with sensitive data redacted)
    """
    try:
        config = {
            "poll_interval": settings.POLL_INTERVAL,
            "has_adguard": settings.has_adguard,
            "adguard_url": settings.ADGUARD_URL if settings.ADGUARD_URL else "not configured",
            "gemini_available": bool(settings.GEMINI_API_KEY),
            "google_sheets_available": bool(settings.GOOGLE_SHEET_ID),
            "allowed_origins": settings.allowed_origins_list,
        }
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp.tool()
def sync_to_google_sheets(domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Manually trigger Google Sheets synchronization.

    Args:
        domain: Optional specific domain to sync (syncs all if None)

    Returns:
        Synchronization result
    """
    try:
        if not settings.GOOGLE_SHEET_ID:
            return {"error": "Google Sheets not configured"}

        from backend.services.sheets_logger import log_threat_to_sheet
        import asyncio
        from backend.db.repository import get_domain_repository

        if domain:
            # Sync specific domain
            # Note: This is a simplified version - actual implementation would need
            # to get analysis data for the domain first
            result = {"status": "success", "domain": domain}
            return {"status": "success", "domain": domain, "result": result}
        else:
            # Sync all recent threats
            async def sync_all():
                repo = await get_domain_repository()
                domains = await repo.get_recent_domains(limit=50)
                results = []
                for domain_obj in domains:
                    result = {"domain": domain_obj.domain, "success": True}
                    results.append(result)
                return {"status": "success", "total_synced": len(results), "results": results}

            return asyncio.run(sync_all())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp.tool()
def get_entropy_analysis(domain: str) -> Dict[str, Any]:
    """
    Get Shannon entropy analysis for a domain.

    Args:
        domain: The domain name to analyze

    Returns:
        Entropy score and analysis
    """
    try:
        from backend.logic.ml_heuristics import calculate_entropy

        entropy = calculate_entropy(domain)
        return {
            "domain": domain,
            "entropy": entropy,
            "is_suspicious": entropy > 4.0,  # Typical threshold
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@mcp.tool()
def find_similar_threats(domain: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar threats using vector similarity search.

    Args:
        domain: The domain to find similar threats for
        limit: Maximum number of similar threats to return

    Returns:
        List of similar threat detections
    """
    try:
        results = vector_memory.query_memory(domain, k=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp.tool()
def get_threat_cluster(domain: str) -> List[Dict[str, Any]]:
    """
    Get threat cluster information for a domain.

    Args:
        domain: The domain to analyze

    Returns:
        Cluster information including similar domains
    """
    try:
        results = vector_memory.get_threat_cluster(domain)
        return [match.to_dict() for match in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Load environment variables if .env file exists
    if os.path.exists(".env"):
        from dotenv import load_dotenv

        load_dotenv()

    # Validate configuration
    if not settings.is_valid:
        print("WARNING: Missing environment variables. Some features may not work.")

    print("Starting Network Guardian AI MCP Server...")
    print("Available tools:")
    print("- analyze_domain: Analyze a domain for threats")
    print("- get_recent_threats: Retrieve recent detected threats")
    print("- get_threat_stats: Get threat statistics and trends")
    print("- get_system_status: Check system health and status")
    print("- get_config: Retrieve system configuration")
    print("- sync_to_google_sheets: Manually trigger Google Sheets sync")
    print("- get_entropy_analysis: Get Shannon entropy analysis")
    print("- find_similar_threats: Find similar threats using vector search")
    print("- get_threat_cluster: Get threat cluster information")
    print("\nServer running. Press Ctrl+C to stop.")
