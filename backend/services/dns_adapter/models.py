"""
DNS Adapter Data Models
Data transfer objects for DNS adapter communications.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DNSQuery:
    """Represents a DNS query from a DNS server log."""

    domain: str
    timestamp: datetime
    client_ip: str
    query_type: str  # A, AAAA, CNAME, etc.
    blocked: bool
    reason: str | None = None
    rule: str | None = None
    filter_id: int | None = None
    elapsed_ms: float | None = None
