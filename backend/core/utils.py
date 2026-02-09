"""
Utility functions for the Network Guardian AI system
"""

from datetime import datetime, timezone

def get_iso_timestamp() -> str:
    """
    Get current timestamp in ISO-8601 format with 'Z' suffix for UTC.
    Standardizes timestamp format across the entire system.
    """
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace("+00:00", "Z")

def ensure_iso_timestamp(timestamp: str) -> str:
    """
    Ensure a timestamp is in proper ISO-8601 format with 'Z' suffix.
    """
    if not timestamp:
        return get_iso_timestamp()
    
    # Remove any existing timezone offset and add Z
    if "+00:00" in timestamp:
        return timestamp.replace("+00:00", "Z")
    elif timestamp.endswith("Z"):
        return timestamp
    else:
        # Assume UTC if no timezone info
        return timestamp + "Z"