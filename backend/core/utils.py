"""
Utility functions for the Network Guardian AI system
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def get_iso_timestamp() -> str:
    """
    Get current timestamp in ISO-8601 format with Sydney timezone (UTC+11).
    """
    sydney_tz = ZoneInfo("Australia/Sydney")
    return datetime.now(sydney_tz).isoformat(timespec="seconds")


def ensure_iso_timestamp(timestamp: str) -> str:
    """
    Ensure a timestamp is in proper ISO-8601 format.
    """
    if not timestamp:
        return get_iso_timestamp()

    # Remove any existing timezone offset
    if "+00:00" in timestamp:
        return timestamp.replace("+00:00", "")
    elif timestamp.endswith("Z"):
        return timestamp[:-1]

    return timestamp
