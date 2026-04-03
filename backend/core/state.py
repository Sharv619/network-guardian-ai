import threading
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

# In-memory buffers for threat events
# Shared between the poller (writer) and the API (reader)
automated_threats: list[dict[str, Any]] = []
manual_scans: list[dict[str, Any]] = []

# Real-time time-series data for trend chart
# Tracks: threats, anomalies, safe in 5-second buckets
trend_buckets: deque = deque(maxlen=60)  # Keep last 5 minutes (60 * 5s)
last_bucket_time: datetime | None = None
trend_lock = threading.Lock()

# Thread-safe callbacks for real-time updates
threat_callbacks: list[Callable] = []
threat_lock = threading.Lock()


def register_threat_callback(callback: Callable):
    """Register a callback to be called when a new threat is detected."""
    with threat_lock:
        threat_callbacks.append(callback)


def unregister_threat_callback(callback: Callable):
    """Unregister a threat callback."""
    with threat_lock:
        threat_callbacks.remove(callback)


def notify_threat_detected(threat_data: dict[str, Any]):
    """Notify all registered callbacks about a new threat."""
    with threat_lock:
        for callback in threat_callbacks:
            try:
                callback(threat_data)
            except Exception as e:
                print(f"Error in threat callback: {e}")


def get_trend_data() -> list[dict[str, Any]]:
    """Get time-series data for trend chart"""
    with trend_lock:
        return list(trend_buckets)


def update_trend_count(is_threat: bool = False, is_anomaly: bool = False, is_safe: bool = False):
    """Update the current trend bucket with new counts"""
    global last_bucket_time
    now = datetime.now()

    with trend_lock:
        # Create new bucket if needed (every 5 seconds)
        if last_bucket_time is None or (now - last_bucket_time).total_seconds() >= 5:
            new_bucket = {
                "time": now.strftime("%H:%M:%S"),
                "threats": 0,
                "anomalies": 0,
                "safe": 0,
            }
            trend_buckets.append(new_bucket)
            last_bucket_time = now

        # Update current bucket
        if trend_buckets:
            bucket = trend_buckets[-1]
            if is_threat:
                bucket["threats"] += 1
            if is_anomaly:
                bucket["anomalies"] += 1
            if is_safe:
                bucket["safe"] += 1
