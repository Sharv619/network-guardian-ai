import json
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..core.state import get_all_scans, get_all_threats, get_threat_count
from ..core.validators import is_valid_domain
from ..db.repository import get_domain_repository
from ..logic.analysis_cache import get_cached_analysis
from ..logic.vector_store import vector_memory
from ..services.ollama_analyzer import analyze_with_ollama, chat_with_ollama
from ..services.sheets_logger import log_threat_to_sheet

router = APIRouter()


class AdvancedChatMessage(BaseModel):
    message: str
    context: dict[str, Any] | None = None
    include_context: bool = True
    search_radius: int = 5
    min_similarity: float = 0.7


class AdvancedChatResponse(BaseModel):
    response: str
    sources: list[str]
    confidence: str
    context: dict[str, Any]


def extract_domain_from_query(query: str) -> str | None:
    """Extract domain name from user query."""
    # Look for domain patterns in the query
    domain_pattern = r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
    matches = re.findall(domain_pattern, query.lower())

    if matches:
        # Return the most likely domain (longest match or first match)
        return max(matches, key=len) if matches else matches[0]

    return None


def search_threat_history(domain: str) -> list[dict[str, Any]]:
    """Search threat history for a specific domain."""
    results = []

    # Search automated threats
    for threat in get_all_threats():
        if domain.lower() in threat.get("domain", "").lower():
            results.append(threat)

    # Search manual scans
    for scan in get_all_scans():
        if domain.lower() in scan.get("domain", "").lower():
            results.append(scan)

    return results


def search_vector_memory(
    query: str, k: int = 5, min_similarity: float = 0.7
) -> list[dict[str, Any]]:
    """Search vector memory for similar threats with enhanced filtering."""
    if vector_memory and vector_memory._available:
        try:
            matches = vector_memory.find_similar_threats(query, k=k, min_similarity=min_similarity)
            return [match.to_dict() for match in matches]
        except Exception as e:
            print(f"Vector memory search error: {e}")
            return []
    return []


def search_analysis_cache(domain: str) -> dict[str, Any] | None:
    """Search analysis cache for domain analysis."""
    # Try to find cached analysis for the domain
    # We'll search with empty metadata to find general domain analysis
    metadata: dict[str, Any] = {}
    cached_result = get_cached_analysis(domain, metadata)
    return cached_result


def get_temporal_context(domain: str) -> dict[str, Any]:
    """Get temporal context for a domain (time-based patterns)."""
    context: dict[str, Any] = {
        "first_seen": None,
        "last_seen": None,
        "frequency": 0,
        "trend": "stable",  # increasing, decreasing, stable
        "recent_activity": [],
    }

    # Search through threat history for temporal patterns
    all_records = get_all_threats() + get_all_scans()
    domain_records = [r for r in all_records if domain.lower() in r.get("domain", "").lower()]

    if domain_records:
        timestamps = [
            r.get("timestamp")
            for r in domain_records
            if r.get("timestamp") and r.get("timestamp") is not None
        ]
        if timestamps:
            # Filter out None values and ensure we have valid timestamps
            valid_timestamps = [ts for ts in timestamps if ts is not None]
            if valid_timestamps:
                context["first_seen"] = min(valid_timestamps)
                context["last_seen"] = max(valid_timestamps)
                context["frequency"] = len(domain_records)

                # Determine trend based on recency
                recent_records = [
                    r
                    for r in domain_records
                    if r.get("timestamp")
                    and r.get("timestamp") is not None
                    and (
                        datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
                        > datetime.now(UTC) - timedelta(hours=24)
                    )
                ]
                context["recent_activity"] = recent_records

                if len(recent_records) > len(domain_records) * 0.5:
                    context["trend"] = "increasing"
                elif len(recent_records) == 0 and len(domain_records) > 5:
                    context["trend"] = "decreasing"

    return context


def get_behavioral_context(domain: str) -> dict[str, Any]:
    """Get behavioral context for a domain (risk patterns)."""
    context = {
        "risk_trend": "stable",  # increasing, decreasing, stable
        "common_categories": [],
        "average_risk_score": 0.0,
        "anomaly_indicators": [],
    }

    domain_records = [
        r
        for r in get_all_threats() + get_all_scans()
        if domain.lower() in r.get("domain", "").lower()
    ]

    if domain_records:
        risk_scores = []
        categories: dict[str, int] = defaultdict(int)

        for record in domain_records:
            risk_score = record.get("risk_score", "Low")
            category = record.get("category", "Unknown")

            # Convert risk score to numeric
            risk_map = {"Low": 1, "Medium": 3, "High": 5, "Critical": 10}
            numeric_score = risk_map.get(risk_score, 1)
            risk_scores.append(numeric_score)
            categories[category] += 1

        if risk_scores:
            avg_risk = sum(risk_scores) / len(risk_scores)
            context["average_risk_score"] = avg_risk
            context["common_categories"] = sorted(
                categories.items(), key=lambda x: x[1], reverse=True
            )[:3]

            # Determine trend
            recent_risks = risk_scores[-5:] if len(risk_scores) >= 5 else risk_scores
            if (
                len(recent_risks) >= 2
                and recent_risks[-1] > sum(recent_risks[:-1]) / len(recent_risks[:-1]) * 1.5
            ):
                context["risk_trend"] = "increasing"
            elif (
                len(recent_risks) >= 2
                and recent_risks[-1] < sum(recent_risks[:-1]) / len(recent_risks[:-1]) * 0.5
            ):
                context["risk_trend"] = "decreasing"

    return context


async def generate_advanced_rag_response(
    request: Request,
    query: str,
    include_context: bool = True,
    search_radius: int = 5,
    min_similarity: float = 0.7,
) -> dict[str, Any]:
    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility
    """Generate advanced RAG response with comprehensive context from multiple sources."""
    response_parts = []
    sources = []
    confidence = "medium"
    context_info = {}

    # Extract domain from query if present
    domain = extract_domain_from_query(query)

    # Initialize threat_history to prevent unbound variable error
    threat_history = []

    # 1. Search threat history
    if domain:
        threat_history = search_threat_history(domain)
        if threat_history:
            response_parts.append(
                f"🔍 Found {len(threat_history)} historical records for domain '{domain}':"
            )
            for _i, threat in enumerate(threat_history[:3]):  # Show top 3
                response_parts.append(
                    f"  • {threat.get('category', 'Unknown')}: {threat.get('risk_score', 'Unknown')} risk - {threat.get('summary', '')}"
                )
            sources.append("threat_history")
            confidence = "high" if threat_history else confidence

    # 2. Search vector memory with enhanced filtering
    vector_results = search_vector_memory(query, k=search_radius, min_similarity=min_similarity)
    if vector_results:
        response_parts.append(f"🧠 Found {len(vector_results)} similar threat patterns:")
        for _i, result in enumerate(vector_results[:3]):  # Show top 3
            similarity = result.get("_similarity_score", 0)
            response_parts.append(
                f"  • Similar to {result.get('domain', 'Unknown')} (similarity: {similarity:.2f})"
            )
            response_parts.append(
                f"    Category: {result.get('category', 'Unknown')}, Risk: {result.get('risk_score', 'Unknown')}"
            )
        sources.append("vector_memory")
        confidence = "high" if vector_results else confidence

    # 3. Search analysis cache
    if domain:
        cached_analysis = search_analysis_cache(domain)
        if cached_analysis:
            response_parts.append(f"💾 Cached analysis for '{domain}':")
            response_parts.append(f"  • Risk: {cached_analysis.get('risk_score', 'Unknown')}")
            response_parts.append(f"  • Category: {cached_analysis.get('category', 'Unknown')}")
            response_parts.append(f"  • Summary: {cached_analysis.get('summary', '')}")
        sources.append("analysis_cache")

    # 4. Get temporal and behavioral context
    if include_context and domain:
        temporal_context = get_temporal_context(domain)
        behavioral_context = get_behavioral_context(domain)

        if temporal_context["frequency"] > 0:
            response_parts.append(f"⏰ Temporal Context for '{domain}':")
            response_parts.append(f"  • First seen: {temporal_context['first_seen']}")
            response_parts.append(f"  • Last seen: {temporal_context['last_seen']}")
            response_parts.append(f"  • Frequency: {temporal_context['frequency']} occurrences")
            response_parts.append(f"  • Trend: {temporal_context['trend']}")

        if behavioral_context["average_risk_score"] > 0:
            response_parts.append(f"📊 Behavioral Context for '{domain}':")
            response_parts.append(
                f"  • Average risk score: {behavioral_context['average_risk_score']:.2f}"
            )
            response_parts.append(f"  • Risk trend: {behavioral_context['risk_trend']}")
            response_parts.append(
                f"  • Common categories: {', '.join([cat for cat, _ in behavioral_context['common_categories'][:2]])}"
            )

    # 5. Perform new analysis if domain found and not in cache
    if domain and not any("analysis_cache" in src for src in sources):
        try:
            analysis = analyze_with_ollama(domain)
            if analysis:
                response_parts.append(f"⚡ New analysis for '{domain}':")
                response_parts.append(f"  • Risk: {analysis.get('risk_score', 'Unknown')}")
                response_parts.append(f"  • Category: {analysis.get('category', 'Unknown')}")
                response_parts.append(f"  • Summary: {analysis.get('summary', '')}")

                # Cache the new analysis
                cache_metadata = {
                    "query": query,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                from ..logic.analysis_cache import cache_analysis_result

                cache_analysis_result(domain, cache_metadata, analysis, "ollama_analysis")

                # Store the analysis in the database for the current tenant
                try:
                    async with get_domain_repository(tenant_id=tenant_id) as repo:
                        await repo.create_domain_from_analysis(analysis)
                except Exception as e:
                    # Log the error but don't fail the request because we still want to return the analysis
                    print(f"Warning: Failed to store analysis for domain {domain}: {e}")

        except Exception as e:
            response_parts.append(f"⚠️ Could not perform new analysis: {str(e)}")

    # 6. If no specific domain found, use general AI chat with enhanced context
    if not response_parts:
        # Enhance the query with security context
        enhanced_query = f"Security context: {query}. Provide relevant cybersecurity information and threat intelligence."
        ai_response = chat_with_ollama(enhanced_query)
        response_parts.append(ai_response)
        sources.append("ai_general")
        confidence = "low"

    # Combine all response parts
    final_response = "\n\n".join(response_parts)

    # Build context information
    if include_context:
        context_info = {
            "domain_found": domain is not None,
            "domain": domain,
            "temporal_context": get_temporal_context(domain) if domain else {},
            "behavioral_context": get_behavioral_context(domain) if domain else {},
            "search_radius": search_radius,
            "min_similarity": min_similarity,
            "result_count": len(vector_results) + len(threat_history),
        }

    return {
        "response": final_response,
        "sources": sources,
        "confidence": confidence,
        "context": context_info,
    }


def format_advanced_chat_response(result: dict[str, Any]) -> str:
    """Format the advanced chat response for better readability."""
    response = result["response"]

    if result["context"].get("domain_found"):
        domain = result["context"]["domain"]
        response = f"🔍 **Domain Analysis for {domain}**:\n{response}"

    if result["sources"]:
        sources_text = ", ".join(result["sources"]).replace("_", " ").title()
        response += f"\n\n📊 **Sources**: {sources_text}"
        response += f"\n🎯 **Confidence**: {result['confidence'].title()}"

    if result["context"].get("result_count", 0) > 0:
        response += f"\n🔗 **Related Items**: {result['context']['result_count']} found"

    return response


@router.post("/chat/advanced")
async def advanced_chat_endpoint(request: Request, chat_request: AdvancedChatMessage):
    message = chat_request.message.strip()
    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility

    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    try:
        # Generate advanced RAG-enhanced response
        rag_result = await generate_advanced_rag_response(
            request,
            message,
            include_context=chat_request.include_context,
            search_radius=chat_request.search_radius,
            min_similarity=chat_request.min_similarity,
        )
        formatted_response = format_advanced_chat_response(rag_result)

        # Log the chat interaction
        chat_log = {
            "query": message,
            "response": formatted_response,
            "sources": rag_result["sources"],
            "confidence": rag_result["confidence"],
            "context": rag_result["context"],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Log to sheets if configured
        try:
            log_threat_to_sheet(
                "Advanced Chat Interaction",
                {
                    "risk_score": rag_result.get("confidence", "N/A"),
                    "category": "Advanced Chat Analysis",
                    "summary": f"Query: {chat_log.get('query', 'N/A')}, Response: {chat_log.get('response', 'N/A')}",
                    "confidence": rag_result.get("confidence", "N/A"),
                    "domain_found": rag_result["context"].get("domain_found", "N/A"),
                },
            )
        except Exception as e:
            print(f"Advanced chat logging error: {e}")

        return {
            "text": formatted_response,
            "sources": rag_result["sources"],
            "confidence": rag_result["confidence"],
            "context": rag_result["context"],
        }

    except Exception as e:
        print(f"Advanced Chat API Error: {e}")
        # Return graceful degradation response
        return {
            "text": "Network Guardian AI: Advanced chat service temporarily unavailable. Basic analysis services remain active."
        }


@router.get("/chat/enhanced-search/{query}")
async def enhanced_search_chat(
    query: str, k: int = 5, min_similarity: float = 0.7, include_context: bool = True
):
    """Enhanced search functionality with multiple data sources and context."""
    if not query:
        raise HTTPException(status_code=422, detail="Query is required")

    # Extract potential domain from query
    domain = extract_domain_from_query(query)

    results: dict[str, Any] = {
        "query": query,
        "domain_extracted": domain,
        "threat_history": [],
        "vector_matches": [],
        "cached_analyses": [],
        "temporal_context": {},
        "behavioral_context": {},
        "total_matches": 0,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Search threat history if domain found
    if domain:
        results["threat_history"] = search_threat_history(domain)

    # Search vector memory with enhanced parameters
    results["vector_matches"] = search_vector_memory(query, k=k, min_similarity=min_similarity)

    # Search analysis cache if domain found
    if domain:
        cached_analysis = search_analysis_cache(domain)
        if cached_analysis:
            results["cached_analyses"] = [cached_analysis]

    # Add context if requested
    if include_context and domain:
        results["temporal_context"] = get_temporal_context(domain)
        results["behavioral_context"] = get_behavioral_context(domain)

    results["total_matches"] = len(results["threat_history"]) + len(results["vector_matches"])

    return results


@router.post("/chat/contextual-analyze")
async def contextual_analyze_endpoint(chat_request: AdvancedChatMessage):
    """Contextual domain analysis with enhanced RAG and temporal awareness."""
    message = chat_request.message.strip()

    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    # Extract domain from message
    domain = extract_domain_from_query(message)

    if not domain:
        # Try to interpret the message differently
        if "analyze" in message.lower() or "scan" in message.lower():
            # Assume the whole message might be a domain
            domain = message.strip()

    if not domain:
        raise HTTPException(status_code=422, detail="No domain found in message")

    if not is_valid_domain(domain):
        raise HTTPException(status_code=422, detail="Invalid domain format")

    try:
        # Check cache first
        cached_result = search_analysis_cache(domain)

        if cached_result:
            response = f" Cached analysis for '{domain}':\n{json.dumps(cached_result, indent=2)}"
        else:
            # Perform new analysis
            analysis = analyze_with_ollama(domain)

            # Cache the result
            cache_metadata = {"query": message, "timestamp": datetime.now(UTC).isoformat()}
            from ..logic.analysis_cache import cache_analysis_result

            cache_analysis_result(domain, cache_metadata, analysis, "contextual_analysis")

            response = f"New analysis for '{domain}':\n{json.dumps(analysis, indent=2)}"

        # Get additional context
        temporal_context = get_temporal_context(domain)
        behavioral_context = get_behavioral_context(domain)

        return {
            "domain": domain,
            "analysis": response,
            "cached": bool(cached_result),
            "temporal_context": temporal_context,
            "behavioral_context": behavioral_context,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e


@router.get("/chat/vector-insights/{query}")
async def get_vector_insights(query: str, k: int = 10):
    """Get insights from vector memory about threat patterns."""
    if not query:
        raise HTTPException(status_code=422, detail="Query is required")

    vector_results = search_vector_memory(query, k=k, min_similarity=0.5)

    insights: dict[str, Any] = {
        "query": query,
        "total_matches": len(vector_results),
        "categories": defaultdict(int),
        "risk_distribution": defaultdict(int),
        "similar_domains": [],
        "common_patterns": [],
        "timestamp": datetime.now(UTC).isoformat(),
    }

    for result in vector_results:
        category = result.get("category", "Unknown")
        risk_score = result.get("risk_score", "Unknown")
        domain = result.get("domain", "")

        insights["categories"][category] += 1
        insights["risk_distribution"][risk_score] += 1
        insights["similar_domains"].append(
            {
                "domain": domain,
                "similarity": result.get("_similarity_score", 0),
                "category": category,
                "risk": risk_score,
            }
        )

    # Get top categories and risk patterns
    insights["top_categories"] = sorted(
        insights["categories"].items(), key=lambda x: x[1], reverse=True
    )[:5]
    insights["risk_breakdown"] = dict(insights["risk_distribution"])

    return insights
