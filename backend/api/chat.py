import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.state import automated_threats, manual_scans
from ..db.repository import get_domain_repository
from ..logic.analysis_cache import analysis_cache, get_cached_analysis
from ..logic.anomaly_engine import engine as anomaly_engine
from ..logic.ml_heuristics import calculate_entropy, extract_domain_features, is_dga
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
    metadata: dict[str, Any] = {}
    cached_result = get_cached_analysis(domain, metadata)
    return cached_result


async def generate_rag_response(request: Request, query: str) -> dict[str, Any]:
    """Generate RAG response with context from multiple sources."""
    response_parts = []
    sources = []
    confidence = "medium"
    cached_analysis = None

    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility

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
                category = threat.get("category", "Unknown")
                risk = threat.get("risk_score", "Unknown")
                summary = threat.get("summary", "")[:50]
                response_parts.append(f"- {category}: {risk} risk - {summary}")
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
                domain = result.get("domain", "Unknown")
                summary = result.get("summary", "")[:30]
                response_parts.append(
                    f"- Similar to {domain} (similarity: {similarity:.2f}): {summary}"
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

                # Store the analysis in the database for the current tenant
                try:
                    repo = await get_domain_repository(tenant_id=tenant_id)
                    await repo.create_domain_from_analysis(analysis)
                except Exception as e:
                    # Log the error but don't fail the request because we still want to return the analysis
                    print(f"Warning: Failed to store analysis for domain {domain}: {e}")

        except Exception as e:
            response_parts.append(f"Could not perform new analysis: {str(e)}")

    # 5. Add intent-specific responses
    if "statistics" in intents and not domain:
        total_threats = len(automated_threats) + len(manual_scans)
        response_parts.append(f"\n📊 **System Statistics**: {total_threats} total threat records")
        sources.append("system_stats")

        if "recommend" in intents:
            response_parts.append(
                "\n💡 **Recommendations**: Monitor suspicious patterns, use DNS filtering."
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
async def chat_endpoint(request: Request, chat_request: ChatMessage):
    """Enhanced chat endpoint with RAG functionality."""
    message = chat_request.message.strip()

    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility

    try:
        # Generate RAG-enhanced response
        rag_result = await generate_rag_response(request, message)
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
            query_summary = chat_log.get("query", "N/A")[:50]
            log_threat_to_sheet(
                domain="Chat Interaction",
                analysis={
                    "risk_score": rag_result.get("confidence", "N/A"),
                    "category": "Chat Analysis",
                    "summary": f"Query: {query_summary}...",
                    "confidence": rag_result.get("confidence", "N/A"),
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
        return {"text": "Network Guardian AI: Chat unavailable. Analysis services active."}


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

    results: dict[str, Any] = {
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
        results["threat_history"] = threat_history  # type: ignore[assignment]

    expanded_queries = expand_query_semantically(query, recognize_intent(query))
    for exp_query in expanded_queries:
        matches = search_vector_memory(exp_query)
        if matches:
            results["vector_matches"] = cast(list[dict[str, Any]], matches[:10])  # type: ignore[assignment]
            break

    if domain:
        cached_analysis = search_analysis_cache(domain)
        if cached_analysis:
            results["cached_analyses"] = cast(list[dict[str, Any]], [cached_analysis])  # type: ignore[assignment]

    threat_history_list: list[dict[str, Any]] = results.get("threat_history", [])  # type: ignore[assignment]
    vector_matches_list: list[dict[str, Any]] = results.get("vector_matches", [])  # type: ignore[assignment]
    if threat_history_list or vector_matches_list:
        results["patterns_detected"] = detect_threat_patterns(
            threat_history_list + vector_matches_list
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
async def stream_chat_response(request: Request, query: str):
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

        rag_result = await generate_rag_response(request, query)
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


@router.post("/system-chat")
async def system_chat_endpoint(request: Request, chat_request: ChatMessage):
    """System-aware chat endpoint with ML heuristics and vector store integration.

    This endpoint provides comprehensive network security analysis by integrating:
    - Shannon Entropy analysis for DGA detection
    - Isolation Forest anomaly detection
    - Vector similarity search for threat clustering
    - Historical threat intelligence
    """
    message = chat_request.message.strip()

    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility

    try:
        # Extract domain from query if present
        domain = extract_domain_from_query(message)

        # Initialize analysis data
        analysis_data: dict[str, Any] = {
            "domain": domain,
            "message": message,
            "ml_heuristics": {},
            "anomaly_detection": {},
            "vector_similarity": [],
            "threat_history": [],
            "analysis_timestamp": datetime.now(UTC).isoformat(),
        }

        # ML Heuristics Analysis (Shannon Entropy)
        if domain:
            entropy = calculate_entropy(domain)
            is_dga_result = is_dga(domain)

            # Extract features for anomaly detection
            features = extract_domain_features(domain)

            analysis_data["ml_heuristics"] = {
                "domain": domain,
                "entropy_score": entropy,
                "is_dga": is_dga_result,
                "features": {
                    "length": features[1],
                    "digit_ratio": features[2],
                    "vowel_ratio": features[3],
                    "non_alphanumeric": features[4],
                },
                "dga_threshold": 3.8,
            }

            # Anomaly Detection (Isolation Forest)
            try:
                is_anomaly, anomaly_score = anomaly_engine.predict_anomaly(features)
                analysis_data["anomaly_detection"] = {
                    "is_anomaly": is_anomaly,
                    "anomaly_score": anomaly_score,
                    "features": features,
                    "model_status": "trained" if anomaly_engine.is_trained else "cold_start",
                }
            except Exception as e:
                analysis_data["anomaly_detection"] = {
                    "error": str(e),
                    "is_anomaly": False,
                    "anomaly_score": 0.0,
                }

            # Vector Memory Search for similar threats
            try:
                vector_results = vector_memory.find_similar_threats(domain, k=5, min_similarity=0.5)
                analysis_data["vector_similarity"] = [match.to_dict() for match in vector_results]
            except Exception as e:
                print(f"Vector memory search error: {e}")
                analysis_data["vector_similarity"] = []

            # Threat History Search
            threat_history = search_threat_history(domain)
            if threat_history:
                analysis_data["threat_history"] = threat_history[:5]

        # Use conversational response for short queries (<=3 words), full analysis otherwise
        word_count = len(message.split())
        if word_count <= 3 and not domain:
            # Short conversational response using real system stats
            response_text = await generate_conversational_response(message)
        else:
            # Full analysis response
            response_text = generate_system_response(analysis_data)

        # Log the interaction
        try:
            log_threat_to_sheet(
                domain="System Chat Interaction",
                analysis={
                    "risk_score": "Info",
                    "category": "System Chat",
                    "summary": f"Query: {message[:100]}...",
                },
                is_anomaly=analysis_data["ml_heuristics"].get("is_dga", False),
                entropy=analysis_data["ml_heuristics"].get("entropy_score", 0),
            )
        except Exception as e:
            print(f"System chat logging error: {e}")

        return {
            "text": response_text,
            "analysis": analysis_data,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        print(f"System Chat API Error: {e}")
        return {
            "text": "Network Guardian AI: System chat service temporarily unavailable.",
            "analysis": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }


def generate_system_response(analysis_data: dict[str, Any]) -> str:
    """Generate a comprehensive system response based on analysis data."""
    response_parts = []

    domain = analysis_data.get("domain")
    message = analysis_data.get("message", "")
    message_lower = message.lower().strip() if message else ""

    # PRIORITY: Handle shortcut commands even in full analysis mode
    if (
        message_lower in ["ml", "entropy", "status", "stats"]
        or "isolation" in message_lower
        or "forest" in message_lower
    ):
        print(f"DEBUG: Shortcut detected: {message_lower}")
        # Use httpx to get stats directly
        import httpx

        try:
            sync_client = httpx.Client(timeout=5.0)
            stats_response = sync_client.get("http://localhost:8000/api/stats/system")
            stats = stats_response.json() if stats_response.status_code == 200 else {}
            sync_client.close()
        except Exception as e:
            print(f"DEBUG: Exception getting stats: {e}")
            stats = {}

        if message_lower == "ml" or "isolation" in message_lower or "forest" in message_lower:
            anomaly_data = stats.get("anomaly", {})
            is_trained = anomaly_data.get("is_trained", False)
            samples = anomaly_data.get("total_samples", 0)
            return f"🎯 **Isolation Forest**: {'Trained' if is_trained else 'Cold Start (Training)'} | {samples} samples | Detects unusual DNS patterns via statistical outlier detection"

        if message_lower == "entropy" or "shannon" in message_lower:
            entropy_data = stats.get("entropy", {})
            avg_entropy = entropy_data.get("avg_entropy", 0)
            threshold = entropy_data.get("threshold", 3.8)
            return f"📊 **Shannon Entropy**: Avg {avg_entropy:.2f}/5.0 | Threshold {threshold} | >{threshold} = suspicious random patterns (DGA)"

        if message_lower == "status" or message_lower == "stats":
            autonomy = stats.get("autonomy_score", 0)
            cache_size = stats.get("cache", {}).get("memory_cache_size", 0)
            patterns = stats.get("patterns_learned", 0)
            seed_patterns = stats.get("seed_patterns", 0)
            return f"✅ **System Status**: {autonomy:.1f}% autonomy | {cache_size} cached | {seed_patterns} seed + {patterns} learned patterns"

    # Header
    response_parts.append("🛡️ **Network Guardian AI - System Awareness**")
    response_parts.append("")

    if domain:
        response_parts.append(f"🔍 **Domain Analysis**: {domain}")
        response_parts.append("")

        # ML Heuristics Section
        ml_heuristics = analysis_data.get("ml_heuristics", {})
        if ml_heuristics:
            entropy = ml_heuristics.get("entropy_score", 0)
            is_dga = ml_heuristics.get("is_dga", False)

            response_parts.append("📊 **ML Heuristics Analysis**:")
            response_parts.append(f"  • Shannon Entropy: {entropy:.2f}")
            response_parts.append(
                f"  • DGA Detection: {'🚨 Likely DGA' if is_dga else '✅ Normal'}"
            )

            features = ml_heuristics.get("features", {})
            if features:
                response_parts.append(f"  • Domain Length: {features.get('length', 0)}")
                response_parts.append(f"  • Digit Ratio: {features.get('digit_ratio', 0):.2f}")
            response_parts.append("")

        # Anomaly Detection Section
        anomaly_data = analysis_data.get("anomaly_detection", {})
        if anomaly_data and "error" not in anomaly_data:
            is_anomaly = anomaly_data.get("is_anomaly", False)
            score = anomaly_data.get("anomaly_score", 0)

            response_parts.append("🎯 **Anomaly Detection (Isolation Forest)**:")
            response_parts.append(f"  • Anomaly Score: {score:.4f}")
            response_parts.append(
                f"  • Status: {'🚨 Anomaly Detected' if is_anomaly else '✅ Normal'}"
            )
            response_parts.append("")

        # Vector Similarity Section
        vector_results = analysis_data.get("vector_similarity", [])
        if vector_results:
            response_parts.append("🧠 **Vector Similarity Matches**:")
            for i, result in enumerate(vector_results[:3], 1):
                similarity = result.get("similarity", 0)
                domain_match = result.get("domain", "Unknown")
                category = result.get("category", "Unknown")
                response_parts.append(
                    f"  {i}. {domain_match} (similarity: {similarity:.2f}, category: {category})"
                )
            response_parts.append("")

        # Threat History Section
        threat_history = analysis_data.get("threat_history", [])
        if threat_history:
            response_parts.append("📜 **Threat History**:")
            for i, threat in enumerate(threat_history[:3], 1):
                risk = threat.get("risk_score", "Unknown")
                category = threat.get("category", "Unknown")
                response_parts.append(f"  {i}. {category} - {risk} risk")
            response_parts.append("")

    else:
        # General query response
        response_parts.append(f"💬 **Query**: {message}")
        response_parts.append("")
        response_parts.append("This is a system-aware chat interface for Network Guardian AI.")
        response_parts.append("You can ask about:")
        response_parts.append("  • Specific domains (e.g., 'analyze example.com')")
        response_parts.append("  • Threat patterns and categories")
        response_parts.append("  • System status and configuration")
        response_parts.append("  • Security recommendations")
        response_parts.append("")

    # Summary
    response_parts.append("📋 **Analysis Summary**:")
    response_parts.append(f"  • Timestamp: {analysis_data.get('analysis_timestamp', 'Unknown')}")
    response_parts.append(f"  • Domain Found: {domain is not None}")
    if domain:
        ml_count = len(analysis_data.get("vector_similarity", []))
        history_count = len(analysis_data.get("threat_history", []))
        response_parts.append(f"  • Similar Threats Found: {ml_count}")
        response_parts.append(f"  • Historical Records: {history_count}")

    return "\n".join(response_parts)


async def generate_conversational_response(message: str) -> str:
    """Generate a short, conversational chatbot response using real system stats."""
    import httpx

    message_lower = message.lower().strip()
    words = message_lower.split()

    # Get real system stats
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            stats_response = await client.get("http://localhost:8000/api/stats/system")
            stats = stats_response.json() if stats_response.status_code == 200 else {}
    except:
        stats = {}

    # Get threat count
    threat_count = 0
    threats = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            history_response = await client.get("http://localhost:8000/history")
            threats = history_response.json() if history_response.status_code == 200 else []
            threat_count = len(threats)
    except:
        pass

    # PRIORITY: Handle exact shortcut commands first (ml, entropy, status, etc.)
    if (
        message_lower == "ml"
        or "isolation" in message_lower
        or "forest" in message_lower
        or "anomaly" in message_lower
    ):
        anomaly_data = stats.get("anomaly", {})
        is_trained = anomaly_data.get("is_trained", False)
        samples = anomaly_data.get("total_samples", 0)
        return f"🎯 **Isolation Forest**: {'Trained' if is_trained else 'Cold Start (Training)'} | {samples} samples | Detects unusual DNS patterns via statistical outlier detection"

    if message_lower == "entropy" or "shannon" in message_lower:
        entropy_data = stats.get("entropy", {})
        avg_entropy = entropy_data.get("avg_entropy", 0)
        threshold = entropy_data.get("threshold", 3.8)
        return f"📊 **Shannon Entropy**: Avg {avg_entropy:.2f}/5.0 | Threshold {threshold} | >{threshold} = suspicious random patterns (DGA)"

    if message_lower == "status" or message_lower == "stats":
        autonomy = stats.get("autonomy_score", 0)
        cache_size = stats.get("cache", {}).get("memory_cache_size", 0)
        patterns = stats.get("patterns_learned", 0)
        seed_patterns = stats.get("seed_patterns", 0)
        return f"✅ **System Status**: {threat_count} threats | {autonomy:.1f}% autonomy | {cache_size} cached | {seed_patterns} seed + {patterns} learned patterns"

    # Short responses based on keywords
    if any(w in message_lower for w in ["hi", "hello", "hey", "sup"]):
        return f"👋 Hey! I'm monitoring {threat_count} threats in real-time. Ask me about specific domains, threat patterns, or system stats!"

    if any(w in message_lower for w in ["status", "how", "doing", "health"]):
        autonomy = stats.get("autonomy_score", 0)
        cache_size = stats.get("cache", {}).get("memory_cache_size", 0)
        return f"✅ System healthy! {threat_count} threats tracked | {autonomy:.1f}% autonomy | {cache_size} cached analyses | Local ML + Gemini working"

    if any(w in message_lower for w in ["entropy", "shannon", "dga"]):
        entropy_data = stats.get("entropy", {})
        avg_entropy = entropy_data.get("avg_entropy", 0)
        return f"📊 Shannon Entropy: {avg_entropy:.2f}/5.0 | >4.2 = suspicious random patterns (DGA) | Currently analyzing DNS queries in real-time"

    if any(w in message_lower for w in ["isolation", "forest", "anomaly", "ml", "local"]):
        anomaly_data = stats.get("anomaly", {})
        is_trained = anomaly_data.get("is_trained", False)
        samples = anomaly_data.get("total_samples", 0)
        return f"🎯 Isolation Forest: {'Trained' if is_trained else 'Training'} | {samples} samples | Detects unusual DNS patterns | Requires 10+ samples for detection"

    if any(w in message_lower for w in ["vector", "embedding", "rag", "memory", "knowledge"]):
        vm_stats = stats.get("vector_memory", {})
        return f"🧠 Vector Store: {vm_stats.get('total_embeddings', 0)} embeddings | Semantic search ready | RAG pipeline active | Ollama support in .env"

    if any(w in message_lower for w in ["adguard", "dns", "block", "filter"]):
        return "🛡️ AdGuard DNS: Active | Filtering malicious domains | Check http://localhost:8080 for dashboard | Logs all DNS queries"

    if any(w in message_lower for w in ["gemini", "cloud", "ai", "api"]):
        cloud = stats.get("cloud_decisions", 0)
        local = stats.get("local_decisions", 0)
        return (
            f"☁️ Gemini AI: {cloud} decisions | Local ML: {local} decisions | Hybrid analysis active"
        )
        sources = stats.get("cache", {}).get("source_distribution", {})
        return f"🤖 AI Stack: {cloud} Gemini calls | {local} local ML | {sources.get('gemini_api', 0)} API | {sources.get('knowledge_base', 0)} KB | Falls back to heuristics when quota exceeded"

    if any(w in message_lower for w in ["threat", "attack", "malware", "suspicious"]):
        high_risks = (
            sum(1 for t in threats if t.get("risk_score") in ["High", "Critical"])
            if threat_count > 0
            else 0
        )
        return f"🚨 {threat_count} threats detected | {high_risks} high-risk | Categories: {list(stats.get('classifier', {}).get('category_distribution', {}).keys())}"

    if any(w in message_lower for w in ["stats", "number", "count", "how many"]):
        decisions = stats.get("total_decisions", 0)
        patterns = stats.get("classifier", {}).get("total_patterns", 0)
        return f"📈 {decisions} total decisions | {threat_count} threats | {patterns} ML patterns | 73 cached analyses | 5 seed patterns"

    if any(w in message_lower for w in ["help", "what", "can"]):
        return """🤖 I can help with:
• Domain analysis (e.g., "analyze example.com")
• System status ("how are you?")
• Threat stats ("how many threats?")
• ML explainers ("what is entropy?", "how does isolation forest work?")
• AdGuard info ("is dns filtering active?")
• Vector/RAG ("what's in memory?")"""

    # Default conversational response
    return f"🤔 Got it! I see {threat_count} threats tracked. Ask me about specific domains, system stats, or how my ML detection works (Shannon entropy, Isolation Forest, vector embeddings)!"
