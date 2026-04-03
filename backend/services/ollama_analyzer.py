"""
Ollama Analyzer - Local LLM for domain analysis and embeddings
"""

import json
import logging
from typing import Any

import numpy as np
import requests

from backend.core.config import settings

logger = logging.getLogger(__name__)


def get_ollama_models() -> list[str]:
    """Get list of available Ollama models from local instance."""
    if not settings.OLLAMA_ENABLED:
        return []

    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.ok:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return models
    except Exception as e:
        logger.warning(f"Failed to get Ollama models: {e}")
    return []


def get_embedding(text: str) -> list[float]:
    """Get embedding for text using Ollama embedding model."""
    if not settings.OLLAMA_ENABLED:
        return _mock_embedding(len(text))

    model = settings.OLLAMA_MODEL or "nomic-embed-text"

    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=10,
        )
        if response.ok:
            data = response.json()
            return data.get("embedding", [])
    except Exception as e:
        logger.warning(f"Ollama embedding failed: {e}")

    return _mock_embedding(len(text))


def _mock_embedding(dimension: int = 384) -> list[float]:
    """Generate a mock embedding when Ollama is unavailable."""
    return np.random.randn(dimension).tolist()


def analyze_with_ollama(
    domain: str,
    context: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict:
    """
    Analyze a domain using local Ollama model.

    Args:
        domain: Domain to analyze
        context: Optional context (AdGuard metadata, entropy, etc.)
        model: Ollama model name (defaults to OLLAMA_CHAT_MODEL)

    Returns:
        Analysis dict with risk_score, category, summary
    """
    if not settings.OLLAMA_ENABLED:
        return {
            "risk_score": "Unknown",
            "category": "Unknown",
            "summary": "Ollama is not enabled. Set OLLAMA_ENABLED=true in environment.",
        }

    model = model or settings.OLLAMA_CHAT_MODEL

    # Build prompt
    entropy = context.get("entropy", "unknown") if context else "unknown"
    reason = context.get("reason", "") if context else ""

    prompt = f"""You are a cybersecurity analyst. Analyze this domain for security risks.

Domain: {domain}
Entropy Score: {entropy}
Block Reason: {reason if reason else "None"}

Respond with a JSON object containing:
{{
  "risk_score": "Low" or "Medium" or "High",
  "category": "General Traffic" or "Malware" or "Phishing" or "Tracking" or "Adware" or "Cryptomining",
  "summary": "Brief explanation (1-2 sentences)"
}}

Only respond with valid JSON, no other text."""

    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=30,
        )

        if response.ok:
            data = response.json()
            result_text = data.get("response", "{}")

            # Parse JSON response
            try:
                result = json.loads(result_text)
                return {
                    "risk_score": result.get("risk_score", "Unknown"),
                    "category": result.get("category", "Unknown"),
                    "summary": result.get("summary", "Analysis complete"),
                    "analysis_source": f"ollama:{model}",
                }
            except json.JSONDecodeError:
                return {
                    "risk_score": "Medium",
                    "category": "Unknown",
                    "summary": result_text[:200],
                    "analysis_source": f"ollama:{model}",
                }
        else:
            logger.warning(f"Ollama API error: {response.status_code}")
            return _ollama_fallback(domain, model)

    except Exception as e:
        logger.warning(f"Ollama analysis failed: {e}")
        return _ollama_fallback(domain, model)


def _ollama_fallback(domain: str, model: str) -> dict:
    """Fallback when Ollama fails - use heuristic analysis."""
    from backend.logic.ml_heuristics import calculate_entropy, is_dga

    entropy = calculate_entropy(domain)
    is_dga_result = is_dga(domain)

    if entropy > 3.8 or is_dga_result:
        return {
            "risk_score": "High",
            "category": "Malware",
            "summary": f"Local ML: High entropy ({entropy:.2f}) or DGA pattern detected",
            "analysis_source": f"ollama:{model}_fallback",
        }
    else:
        return {
            "risk_score": "Low",
            "category": "General Traffic",
            "summary": f"Local ML: Normal entropy ({entropy:.2f})",
            "analysis_source": f"ollama:{model}_fallback",
        }


def chat_with_ollama(message: str, context: dict[str, Any] | None = None) -> str:
    """
    Conversational chat using local Ollama model.

    Args:
        message: User message
        context: Optional context about the system state

    Returns:
        Response string from Ollama
    """
    if not settings.OLLAMA_ENABLED:
        return "Ollama is not enabled. Set OLLAMA_ENABLED=true to use local AI chat."

    model = settings.OLLAMA_CHAT_MODEL
    system_prompt = """You are Network Guardian AI, a cybersecurity assistant.
You analyze DNS queries, detect threats, and explain security findings.
Be concise and technical. Use data from the context when available."""

    context_info = ""
    if context:
        context_info = f"\nContext: {json.dumps(context, indent=2)}"

    prompt = f"""{system_prompt}

User: {message}{context_info}

Respond helpfully and concisely."""

    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=30,
        )

        if response.ok:
            data = response.json()
            return data.get("response", "No response from Ollama.")
        else:
            return f"Ollama API error: {response.status_code}. Falling back to local analysis."
    except Exception as e:
        return f"Ollama chat failed: {e}. The local AI is currently unavailable."
