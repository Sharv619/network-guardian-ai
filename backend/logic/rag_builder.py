"""
RAG Prompt Builder - Formats threat data for Gemini context.

Builds context strings from search results for the RAG pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.db.models import ThreatEntry
from backend.logic.vector_store import ThreatMatch, ThreatRecord


@dataclass
class FormattedThreat:
    """Formatted threat for context display."""

    timestamp: str
    domain: str
    category: str
    risk_score: str
    reason: str
    summary: str
    similarity: float | None = None


def format_threat_entry(threat: ThreatEntry) -> FormattedThreat:
    """Format a ThreatEntry for context display."""
    reason = ""
    if threat.threat_metadata and threat.threat_metadata.reason:
        reason = threat.threat_metadata.reason

    timestamp = ""
    if threat.timestamp:
        if isinstance(threat.timestamp, datetime):
            timestamp = threat.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp = str(threat.timestamp)

    return FormattedThreat(
        timestamp=timestamp,
        domain=threat.domain,
        category=threat.category,
        risk_score=threat.risk_score,
        reason=reason,
        summary=threat.summary or "",
    )


def format_threat_match(match: ThreatMatch) -> FormattedThreat:
    """Format a ThreatMatch for context display."""
    reason = ""
    if match.record.metadata:
        reason = match.record.metadata.get("reason", "")

    return FormattedThreat(
        timestamp=match.record.timestamp,
        domain=match.record.domain,
        category=match.record.category,
        risk_score=match.record.risk_score,
        reason=reason,
        summary=match.record.summary,
        similarity=match.similarity,
    )


def format_threat_record(record: ThreatRecord) -> FormattedThreat:
    """Format a ThreatRecord for context display."""
    reason = ""
    if record.metadata:
        reason = record.metadata.get("reason", "")

    return FormattedThreat(
        timestamp=record.timestamp,
        domain=record.domain,
        category=record.category,
        risk_score=record.risk_score,
        reason=reason,
        summary=record.summary,
        similarity=record.metadata.get("similarity") if record.metadata else None,
    )


def format_as_context_line(threat: FormattedThreat) -> str:
    """Format a single threat as a context line."""
    parts = [
        f"[{threat.timestamp}]" if threat.timestamp else "[Unknown]",
        f"Domain: {threat.domain}",
        f"Category: {threat.category}",
        f"Risk: {threat.risk_score}",
    ]

    if threat.reason:
        parts.append(f"Reason: {threat.reason}")

    if threat.summary:
        summary_preview = threat.summary[:100]
        if len(threat.summary) > 100:
            summary_preview += "..."
        parts.append(f"Summary: {summary_preview}")

    if threat.similarity is not None:
        parts.append(f"Similarity: {threat.similarity:.2f}")

    return " | ".join(parts)


def build_rag_context(
    results: list[Any],
    max_results: int = 5,
    include_header: bool = True,
) -> str:
    """
    Build a RAG context string from search results.

    Args:
        results: List of ThreatEntry, ThreatMatch, or ThreatRecord
        max_results: Maximum number of results to include
        include_header: Whether to include the header line

    Returns:
        Formatted context string for Gemini
    """
    if not results:
        return "No relevant threat data found."

    context_lines = []

    if include_header:
        context_lines.append("=== RELEVANT THREAT INTELLIGENCE ===")
        context_lines.append("")

    formatted_threats: list[FormattedThreat] = []

    for result in results[:max_results]:
        if isinstance(result, ThreatEntry):
            formatted_threats.append(format_threat_entry(result))
        elif isinstance(result, ThreatMatch):
            formatted_threats.append(format_threat_match(result))
        elif isinstance(result, ThreatRecord):
            formatted_threats.append(format_threat_record(result))
        elif isinstance(result, dict):
            formatted_threats.append(
                FormattedThreat(
                    timestamp=result.get("timestamp", ""),
                    domain=result.get("domain", ""),
                    category=result.get("category", ""),
                    risk_score=result.get("risk_score", ""),
                    reason=result.get("reason", ""),
                    summary=result.get("summary", ""),
                    similarity=result.get("similarity"),
                )
            )

    for threat in formatted_threats:
        context_lines.append(format_as_context_line(threat))

    context_lines.append("")
    context_lines.append(f"(Showing {len(formatted_threats)} of {len(results)} results)")

    return "\n".join(context_lines)


def build_rag_context_for_gemini(
    query: str,
    results: list[Any],
    max_results: int = 5,
) -> str:
    """
    Build a complete RAG context string with query reference.

    Args:
        query: The original user query
        results: List of search results
        max_results: Maximum results to include

    Returns:
        Complete context string with query and results
    """
    context = f"Query: {query}\n\n"
    context += build_rag_context(results, max_results=max_results, include_header=True)
    return context


def format_threats_for_streaming(threats: list[ThreatEntry]) -> list[dict[str, Any]]:
    """
    Format threats for streaming response.

    Args:
        threats: List of ThreatEntry objects

    Returns:
        List of dictionaries suitable for JSON streaming
    """
    return [
        {
            "domain": threat.domain,
            "risk_score": threat.risk_score,
            "category": threat.category,
            "summary": threat.summary,
            "timestamp": threat.timestamp.isoformat() if threat.timestamp else None,
            "is_anomaly": threat.is_anomaly,
            "anomaly_score": threat.anomaly_score,
            "reason": threat.threat_metadata.reason if threat.threat_metadata else None,
            "client": threat.threat_metadata.client_ip if threat.threat_metadata else None,
        }
        for threat in threats
    ]
