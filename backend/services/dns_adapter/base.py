"""
DNS Adapter Base Interface
Abstract base class for DNS server adapters.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from .models import DNSQuery


class DNSAdapter(ABC):
    """Abstract base class for DNS server adapters."""

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to DNS server.

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def poll_logs(self, since: datetime | None = None) -> list[DNSQuery]:
        """
        Poll DNS query logs since given time.

        Args:
            since: Only return logs after this timestamp (None for all)

        Returns:
            List[DNSQuery]: List of DNS query objects
        """
        pass

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """
        Test connection to DNS server.

        Returns:
            tuple[bool, str]: (success, message)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter name for UI display."""
        pass

    @property
    @abstractmethod
    def supported_features(self) -> list[str]:
        """List of supported features."""
        pass
