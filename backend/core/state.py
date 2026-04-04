import threading
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

# In-memory buffers for threat events
# Shared between the poller (writer) and the API (reader)
automated_threats: deque[dict[str, Any]] = deque(maxlen=500)
manual_scans: deque[dict[str, Any]] = deque(maxlen=100)
_data_lock = threading.Lock()

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


def append_threat(threat: dict[str, Any]) -> None:
    """Thread-safe: add a threat to the front of the deque."""
    with _data_lock:
        automated_threats.appendleft(threat)


def pop_threat() -> dict[str, Any] | None:
    """Thread-safe: remove and return the oldest threat."""
    with _data_lock:
        if automated_threats:
            return automated_threats.pop()
        return None


def get_threats(limit: int = 50) -> list[dict[str, Any]]:
    """Thread-safe: get a copy of the threat list."""
    with _data_lock:
        from itertools import islice

        return list(islice(automated_threats, limit))


def get_threat_count() -> int:
    """Thread-safe: get the number of threats."""
    with _data_lock:
        return len(automated_threats)


def append_scan(scan: dict[str, Any]) -> None:
    """Thread-safe: add a manual scan to the front of the deque."""
    with _data_lock:
        manual_scans.appendleft(scan)


def get_scans(limit: int = 50) -> list[dict[str, Any]]:
    """Thread-safe: get a copy of the manual scans list."""
    with _data_lock:
        from itertools import islice

        return list(islice(manual_scans, limit))


def get_all_threats() -> list[dict[str, Any]]:
    """Thread-safe: get a full copy of all threats."""
    with _data_lock:
        return list(automated_threats)


def get_all_scans() -> list[dict[str, Any]]:
    """Thread-safe: get a full copy of all scans."""
    with _data_lock:
        return list(manual_scans)
