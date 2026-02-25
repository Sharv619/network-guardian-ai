import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.state import automated_threats, manual_scans
from ..logic.analysis_cache import analysis_cache, get_cached_analysis
from ..logic.vector_store import vector_memory
from ..services.gemini_analyzer import analyze_domain, chat_with_ai
from ..services.sheets_logger import log_threat_to_sheet

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: str
    sources: list[str]
    confidence: str


class SearchQuery(BaseModel):
    query: str
    filters: dict[str, Any] | None = None


INTENT_PATTERNS = {
    "analyze": [
        r"\b(analy[sz]|scan|check|examine|investigate|inspect|review)\b",
        r"\b(look\s+up|find\s+info|get\s+info|show\s+me)\b",
    ],
    "compare": [
        r"\b(compare|match|similar|like|vs|versus|versus)\b",
        r"\b(difference|different|relate)\b",
    ],
    "history": [
        r"\b(history|past|previous|earlier|old|recent)\b",
        r"\b(when|last|first|time|dated)\b",
    ],
    "statistics": [
        r"\b(stat|stats|count|number|how\s+many|total)\b",
        r"\b(summary|overview|dashboard|metrics)\b",
    ],
    "threat_intel": [
        r"\b(threat|malware|phishing|scam|fraud|suspicious)\b",
        r"\b(dangerous|unsafe|risky|malicious|malware)\b",
    ],
    "recommend": [
        r"\b(recommend|suggest|advice|should\s+I|what\s+to\s+do)\b",
        r"\b(best|optimal|better|prefer)\b",
    ],
    "general": [],
}


def recognize_intent(query: str) -> list[str]:
    """Recognize user intent from query using pattern matching."""
    query_lower = query.lower()
    intents = []

    for intent, patterns in INTENT_PATTERNS.items():
        if intent == "general":
            continue
        for pattern in patterns:
            if re.search(pattern, query_lower):
                intents.append(intent)
                break

    if not intents:
        intents.append("general")

    return intents


def expand_query_semantically(query: str, intents: list[str]) -> list[str]:
    """Expand query with semantically related terms for better vector search."""
    expansions = [query]

    intent_expansions = {
        "analyze": ["domain analysis", "risk assessment", "security check"],
        "compare": ["similar threats", "related domains", "comparison"],
        "history": ["past threats", "historical data", "previous analysis"],
        "statistics": ["threat statistics", "metrics", "overview"],
        "threat_intel": ["malware", "phishing", "suspicious", "malicious domain"],
        "recommend": ["security recommendations", "best practices", "advice"],
    }

    for intent in intents:
        if intent in intent_expansions:
            for expansion in intent_expansions[intent]:
                expansions.append(expansion)

    if "domain" not in query.lower():
        expansions.append("domain security")

    return expansions[:5]


def filter_by_time_range(
    records: list[dict[str, Any]], time_range: str | None = None
) -> list[dict[str, Any]]:
    """Filter records by time range (hour, day, week, month)."""
    if not time_range:
        return records

    now = datetime.now(UTC)
    range_map = {
        "hour": timedelta(hours=1),
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30),
    }

    delta = range_map.get(time_range.lower())
    if not delta:
        return records

    cutoff = now - delta
    filtered = []

    for record in records:
        try:
            record_time_str = record.get("timestamp", "")
            if record_time_str:
                record_time = datetime.fromisoformat(record_time_str.replace("Z", "+00:00"))
                if record_time >= cutoff:
                    filtered.append(record)
        except Exception:
            filtered.append(record)

    return filtered


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
    for threat in automated_threats:
        if domain.lower() in threat.get("domain", "").lower():
            results.append(threat)

    # Search manual scans
    for scan in manual_scans:
        if domain.lower() in scan.get("domain", "").lower():
            results.append(scan)

    return results


def search_vector_memory(query: str) -> list[dict[str, Any]]:
    """Search vector memory for similar threats."""
    if vector_memory:
        try:
            matches = vector_memory.find_similar_threats(query, k=5)
            return [match.to_dict() for match in matches]
        except Exception as e:
            print(f"Vector memory search error: {e}")
            return []
    return []


def search_analysis_cache(domain: str) -> dict[str, Any] | None:
    """Search analysis cache for domain analysis."""
    # Try to find cached analysis for the domain
    # We'll search with empty metadata to find general domain analysis
    metadata = {}
    cached_result = get_cached_analysis(domain, metadata)
    return cached_result


def generate_rag_response(query: str) -> dict[str, Any]:
    """Generate RAG response with context from multiple sources."""
    response_parts = []
    sources = []
    confidence = "medium"
    cached_analysis = None

    intents = recognize_intent(query)
    query_expansions = expand_query_semantically(query, intents)

    # Extract domain from query if present
    domain = extract_domain_from_query(query)

    # 1. Search threat history with time filtering if requested
    if domain:
        threat_history = search_threat_history(domain)
        if threat_history:
            response_parts.append(
                f"Found {len(threat_history)} historical records for domain '{domain}':"
            )
            for _, threat in enumerate(threat_history[:3]):
                response_parts.append(
                    f"- {threat.get('category', 'Unknown')}: {threat.get('risk_score', 'Unknown')} risk - {threat.get('summary', '')}"
                )
            sources.append("threat_history")
            confidence = "high" if threat_history else confidence

    # 2. Search vector memory with expanded queries
    vector_results = []
    for expanded_query in query_expansions:
        vector_results = search_vector_memory(expanded_query)
        if vector_results:
            break

    if vector_results:
        response_parts.append(f"Found {len(vector_results)} similar threat patterns:")
        for _, result in enumerate(vector_results[:3]):
            similarity = result.get("_similarity_score", 0)
            response_parts.append(
                f"- Similar to {result.get('domain', 'Unknown')} (similarity: {similarity:.2f}): {result.get('summary', '')}"
            )
        sources.append("vector_memory")
        confidence = "high" if vector_results else confidence

    # 3. Search analysis cache
    if domain:
        cached_analysis = search_analysis_cache(domain)
        if cached_analysis:
            response_parts.append(f"Cached analysis for '{domain}':")
            response_parts.append(f"- Risk: {cached_analysis.get('risk_score', 'Unknown')}")
            response_parts.append(f"- Category: {cached_analysis.get('category', 'Unknown')}")
            response_parts.append(f"- Summary: {cached_analysis.get('summary', '')}")
        sources.append("analysis_cache")

    # 4. Perform new analysis if domain found and not in cache
    if domain and not cached_analysis:
        try:
            analysis = analyze_domain(domain)
            if analysis:
                response_parts.append(f"New analysis for '{domain}':")
                response_parts.append(f"- Risk: {analysis.get('risk_score', 'Unknown')}")
                response_parts.append(f"- Category: {analysis.get('category', 'Unknown')}")
                response_parts.append(f"- Summary: {analysis.get('summary', '')}")

                # Cache the new analysis
                cache_metadata = {
                    "query": query,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "intents": intents,
                }
                from ..logic.analysis_cache import cache_analysis_result

                cache_analysis_result(domain, cache_metadata, analysis, "gemini_analysis")

        except Exception as e:
            response_parts.append(f"Could not perform new analysis: {str(e)}")

    # 5. Add intent-specific responses
    if "statistics" in intents and not domain:
        total_threats = len(automated_threats) + len(manual_scans)
        response_parts.append(f"\n📊 **System Statistics**: {total_threats} total threat records")
        sources.append("system_stats")

    if "recommend" in intents:
        response_parts.append(
            "\n💡 **Recommendations**: Monitor for suspicious patterns, use DNS filtering, enable threat intelligence feeds."
        )
        sources.append("recommendations")

    # 6. If no specific domain found, use general AI chat
    if not response_parts:
        ai_response = chat_with_ai(query)
        response_parts.append(ai_response)
        sources.append("ai_general")
        confidence = "low"

    # Combine all response parts
    final_response = "\n\n".join(response_parts)

    return {
        "response": final_response,
        "sources": sources,
        "confidence": confidence,
        "domain_found": domain is not None,
        "intents": intents,
    }


def format_chat_response(result: dict[str, Any]) -> str:
    """Format the chat response for better readability."""
    response = result["response"]

    if result["domain_found"]:
        response = f"🔍 **Domain Analysis**:\n{response}"

    if result["sources"]:
        sources_text = ", ".join(result["sources"]).replace("_", " ").title()
        response += f"\n\n📊 **Sources**: {sources_text}"
        response += f"\n🎯 **Confidence**: {result['confidence'].title()}"

    return response


@router.post("/chat")
async def chat_endpoint(chat_request: ChatMessage):
    """Enhanced chat endpoint with RAG functionality."""
    message = chat_request.message.strip()

    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    try:
        # Generate RAG-enhanced response
        rag_result = generate_rag_response(message)
        formatted_response = format_chat_response(rag_result)

        # Log the chat interaction
        chat_log = {
            "query": message,
            "response": formatted_response,
            "sources": rag_result["sources"],
            "confidence": rag_result["confidence"],
            "domain_found": rag_result["domain_found"],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Log to sheets if configured
        try:
            log_threat_to_sheet(
                "Chat Interaction",
                {
                    "risk_score": rag_result.get("confidence", "N/A"),
                    "category": "Chat Analysis",
                    "summary": f"Query: {chat_log.get('query', 'N/A')}, Response: {chat_log.get('response', 'N/A')}",
                    "confidence": rag_result.get("confidence", "N/A"),
                    "domain_found": chat_log.get("domain_found", "N/A"),
                },
            )
        except Exception as e:
            print(f"Chat logging error: {e}")

        # For backward compatibility with existing frontend, return simple text response
        # The frontend expects a "text" field, not the ChatResponse object
        return {"text": formatted_response}

    except Exception as e:
        print(f"Chat API Error: {e}")
        # Return graceful degradation response
        return {
            "text": "Network Guardian AI: Chat service temporarily unavailable. Analysis services remain active."
        }


@router.get("/chat/memory-stats")
async def get_memory_stats():
    """Get statistics about the chat memory and RAG components."""
    cache_stats = analysis_cache.get_stats()

    vector_stats = {}
    if vector_memory:
        vector_stats = vector_memory.get_memory_stats()

    return {
        "analysis_cache": cache_stats,
        "vector_memory": vector_stats,
        "automated_threats_count": len(automated_threats),
        "manual_scans_count": len(manual_scans),
        "total_threat_records": len(automated_threats) + len(manual_scans),
    }


@router.get("/chat/search/{query}")
async def search_chat(query: str):
    """Search functionality for chat - allows searching across all data sources."""
    if not query:
        raise HTTPException(status_code=422, detail="Query is required")

    # Extract potential domain from query
    domain = extract_domain_from_query(query)

    results = {
        "query": query,
        "domain_extracted": domain,
        "threat_history": [],
        "vector_matches": [],
        "cached_analyses": [],
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Search threat history if domain found
    if domain:
        results["threat_history"] = search_threat_history(domain)

    # Search vector memory
    results["vector_matches"] = search_vector_memory(query)

    # Search analysis cache if domain found
    if domain:
        cached_analysis = search_analysis_cache(domain)
        if cached_analysis:
            results["cached_analyses"] = [cached_analysis]

    return results


@router.post("/chat/domain-analyze")
async def analyze_domain_chat(chat_request: ChatMessage):
    """Specialized endpoint for domain analysis through chat interface."""
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

    try:
        # Check cache first
        cached_result = search_analysis_cache(domain)

        if cached_result:
            response = f" Cached analysis for '{domain}':\n{json.dumps(cached_result, indent=2)}"
        else:
            # Perform new analysis
            analysis = analyze_domain(domain)

            # Cache the result
            cache_metadata = {"query": message, "timestamp": datetime.now(UTC).isoformat()}
            from ..logic.analysis_cache import cache_analysis_result

            cache_analysis_result(domain, cache_metadata, analysis, "domain_analysis")

            response = f"New analysis for '{domain}':\n{json.dumps(analysis, indent=2)}"

        return {
            "domain": domain,
            "analysis": response,
            "cached": bool(cached_result),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e


@router.post("/chat/search/advanced")
async def advanced_search(search_query: SearchQuery):
    """Advanced multi-faceted search with filters."""
    query = search_query.query.strip()
    filters = search_query.filters or {}

    if not query:
        raise HTTPException(status_code=422, detail="Query is required")

    domain = extract_domain_from_query(query)
    time_range = filters.get("time_range")
    category = filters.get("category")
    min_risk = filters.get("min_risk_score")

    results = {
        "query": query,
        "domain_extracted": domain,
        "intents": recognize_intent(query),
        "filters_applied": filters,
        "threat_history": [],
        "vector_matches": [],
        "cached_analyses": [],
        "patterns_detected": [],
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if domain:
        threat_history = search_threat_history(domain)
        if time_range:
            threat_history = filter_by_time_range(threat_history, time_range)
        if category:
            threat_history = [
                t for t in threat_history if t.get("category", "").lower() == category.lower()
            ]
        if min_risk:
            threat_history = [t for t in threat_history if t.get("risk_score", "low") >= min_risk]
        results["threat_history"] = threat_history

    expanded_queries = expand_query_semantically(query, recognize_intent(query))
    for exp_query in expanded_queries:
        matches = search_vector_memory(exp_query)
        if matches:
            results["vector_matches"] = matches[:10]
            break

    if domain:
        cached_analysis = search_analysis_cache(domain)
        if cached_analysis:
            results["cached_analyses"] = [cached_analysis]

    if results["threat_history"] or results["vector_matches"]:
        results["patterns_detected"] = detect_threat_patterns(
            results["threat_history"] + [v for v in results["vector_matches"]]
        )

    return results


def detect_threat_patterns(records: list[dict[str, Any]]) -> list[str]:
    """Detect common threat patterns from records."""
    patterns = []
    categories = set()
    risk_scores = []

    for record in records:
        if record.get("category"):
            categories.add(record.get("category"))
        risk_score = record.get("risk_score", "")
        if risk_score in ["critical", "high", "medium", "low"]:
            risk_scores.append(risk_score)

    if "phishing" in categories:
        patterns.append("Phishing campaign detected")
    if "malware" in categories:
        patterns.append("Malware distribution detected")
    if "cryptomining" in categories:
        patterns.append("Cryptomining activity detected")

    if risk_scores:
        high_risk_count = sum(1 for r in risk_scores if r in ["critical", "high"])
        if high_risk_count > 2:
            patterns.append("High-risk campaign pattern detected")

    return patterns


@router.get("/chat/stream/{query}")
async def stream_chat_response(query: str):
    """Streaming chat response for real-time feedback."""

    async def generate():
        intents = recognize_intent(query)
        yield f"data: {json.dumps({'type': 'intent', 'data': intents})}\n\n"

        domain = extract_domain_from_query(query)
        if domain:
            yield f"data: {json.dumps({'type': 'domain', 'data': domain})}\n\n"

            cached = search_analysis_cache(domain)
            if cached:
                yield f"data: {json.dumps({'type': 'cache_hit', 'data': True})}\n\n"

        rag_result = generate_rag_response(query)
        formatted = format_chat_response(rag_result)

        yield f"data: {json.dumps({'type': 'response', 'data': formatted})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'data': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/chat/threats/recent")
async def get_recent_threats(limit: int = 10, time_range: str | None = "day"):
    """Get recent threats with optional time filtering."""
    all_threats = list(automated_threats) + list(manual_scans)

    if time_range:
        all_threats = filter_by_time_range(all_threats, time_range)

    all_threats.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "threats": all_threats[:limit],
        "total_count": len(all_threats),
        "time_range": time_range,
        "timestamp": datetime.now(UTC).isoformat(),
    }
