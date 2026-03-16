"""
DNS Adapter Data Models
Data transfer objects for DNS adapter communications.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DNSQuery:
    """Represents a DNS query from a DNS server log."""

    domain: str
    timestamp: datetime
    client_ip: str
    query_type: str  # A, AAAA, CNAME, etc.
    blocked: bool
    reason: Optional[str] = None
    rule: Optional[str] = None
    filter_id: Optional[int] = None
    elapsed_ms: Optional[float] = None
