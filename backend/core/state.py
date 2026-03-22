import threading
from collections.abc import Callable
from typing import Any

# In-memory buffers for threat events
# Shared between the poller (writer) and the API (reader)
automated_threats: list[dict[str, Any]] = []
manual_scans: list[dict[str, Any]] = []

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
