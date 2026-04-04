# Ollama Throttling Plan

## Problem
- `analyze_with_ollama()` is called synchronously with a 30s timeout
- Poller processes domains sequentially — if 10 Medium/High-risk domains arrive, that's up to 5 minutes of blocking
- API endpoints (`chat.py`, `router.py`, `advanced_chat.py`) call Ollama concurrently from HTTP requests with zero protection
- No cooldown between calls — Ollama gets hammered

## Solution: Shared Semaphore + Poller Cooldown

### 1. `backend/core/config.py` — Add configurable settings

**Location:** After line 43 (after `OLLAMA_LIVE_FEED_ENABLED`)

```python
    OLLAMA_MAX_CONCURRENT: int = Field(
        2, ge=1, le=10, description="Max concurrent Ollama requests (prevents resource exhaustion)"
    )
    OLLAMA_CALL_COOLDOWN: float = Field(
        2.0, ge=0, description="Seconds between Ollama calls in poller"
    )
```

### 2. `backend/services/ollama_analyzer.py` — Add shared semaphore

**Add at top of file (after imports, before first function):**

```python
import threading

# Shared semaphore: limits concurrent Ollama calls across ALL callers
# (poller thread + API endpoint threads)
_ollama_semaphore = threading.Semaphore(settings.OLLAMA_MAX_CONCURRENT)
```

**Wrap `analyze_with_ollama()` — the `requests.post()` call at line 105:**

```python
    try:
        with _ollama_semaphore:
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
```

**Wrap `chat_with_ollama()` — the `requests.post()` call at line 198:**

```python
    try:
        with _ollama_semaphore:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=30,
            )
```

**Wrap `get_embedding()` — the `requests.post()` call at line 41:**

```python
    try:
        with _ollama_semaphore:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=10,
            )
```

### 3. `backend/services/adguard_poller.py` — Add cooldown after Ollama call

**Location:** In `run_local_first_pipeline()`, after the Ollama enhancement block (around line 269, inside the `try` block, after the `if "fallback" not in source:` block succeeds).

Add `import time` at the top of the file (line 5 area, it's already imported at line 5).

Inside the Ollama enhancement block, after line 267 (after the `print(f"[OLLAMA ENHANCEMENT] ✅ Enhanced...")`), add:

```python
            time.sleep(settings.OLLAMA_CALL_COOLDOWN)
```

So the block becomes:

```python
            if ollama_analysis and ollama_analysis.get("risk_score"):
                source = ollama_analysis.get("analysis_source", "")
                if "fallback" not in source:
                    local_analysis["summary"] = ollama_analysis.get(
                        "summary", local_analysis["summary"]
                    )
                    local_analysis["analysis_source"] = "ollama_ai_enhanced"
                    local_analysis["confidence"] = ollama_analysis.get("confidence", 0.8)
                    print(
                        f"[OLLAMA ENHANCEMENT] ✅ Enhanced {domain}: {ollama_analysis.get('category')}"
                    )
                    time.sleep(settings.OLLAMA_CALL_COOLDOWN)
```

## How It Works

1. **Semaphore (concurrency limit):** Only 2 threads can hit Ollama at once, regardless of source (poller or API). Additional callers block until a slot frees up. The 30s timeout ensures slots don't stay blocked forever.

2. **Cooldown (rate limit):** After each successful Ollama enhancement in the poller, sleep for 2 seconds before processing the next domain. This prevents back-to-back hammering.

3. **Combined effect:** Even if 50 domains arrive in one poll cycle:
   - Max 2 concurrent Ollama calls
   - 2s cooldown between each
   - Total time: ~50s instead of ~25 minutes of uncontrolled processing
   - Laptop stays cool

## Environment Variables (optional overrides)

```bash
OLLAMA_MAX_CONCURRENT=1    # Ultra-conservative (1 at a time)
OLLAMA_MAX_CONCURRENT=3    # More throughput if your machine can handle it
OLLAMA_CALL_COOLDOWN=1.0   # Faster cooldown
OLLAMA_CALL_COOLDOWN=5.0   # More conservative
```
