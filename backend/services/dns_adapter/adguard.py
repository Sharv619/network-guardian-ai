"""
AdGuard DNS Adapter
Implementation of DNSAdapter for AdGuard Home.
"""

from datetime import UTC, datetime
from typing import List, Optional

import requests

from backend.core.config import settings
from backend.logic.ml_heuristics import is_valid_domain
from .base import DNSAdapter
from .models import DNSQuery


class AdGuardAdapter(DNSAdapter):
    """AdGuard Home DNS adapter."""

    def __init__(self):
        self._session = None
        self._processed_domains = set()
        self._initialize_session()

    def _initialize_session(self):
        """Initialize the requests session with auth if needed."""
        self._session = requests.Session()
        if settings.ADGUARD_USER and settings.ADGUARD_PASS:
            self._session.auth = (settings.ADGUARD_USER, settings.ADGUARD_PASS)
        self._session.headers.update({"Accept": "application/json"})

    def connect(self) -> bool:
        """
        Establish connection to AdGuard.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            success, _ = self.test_connection()
            return success
        except Exception:
            return False

    def poll_logs(self, since: Optional[datetime] = None) -> List[DNSQuery]:
        """
        Poll AdGuard query logs since given time.

        Args:
            since: Only return logs after this timestamp (None for all)

        Returns:
            List[DNSQuery]: List of DNS query objects
        """
        # SRE Pattern: Use persistent sessions for repeated polling
        target_urls = []

        # Add configured URL if available
        if settings.ADGUARD_URL:
            configured_url = f"{settings.ADGUARD_URL}/control/querylog"
            target_urls.append(configured_url)

        # Add fallback URLs - AdGuard Home typically runs on port 80 for the control API
        target_urls.extend(
            [
                "http://adguard:80/control/querylog",
                "http://adguard:3000/control/querylog",
                "http://localhost:80/control/querylog",
            ]
        )

        success = False
        r = None
        for url in target_urls:
            try:
                # Skip empty URLs if any
                if "://" not in url:
                    continue

                r = self._session.get(url, timeout=5)

                if r.status_code == 200:
                    success = True
                    break
                elif r.status_code == 401:
                    # Auth failed, don't try other URLs
                    print(f"CRITICAL: AdGuard Auth Failed at {url}. Check credentials.")
                    break
            except requests.exceptions.RequestException:
                continue

        if not success:
            print("AdGuard Poller: Could not connect to any AdGuard instance.")
            return []

        if r is None:
            print("AdGuard Response Error: No response received")
            return []

        content_type = r.headers.get("Content-Type", "")
        try:
            logs = r.json().get("data", [])
        except ValueError:
            print(f"AdGuard Response Error: Not JSON. Content-Type: {content_type}")
            print(f"Response starts with: {r.text[:100]}")
            return []

        # Process logs into DNSQuery objects
        dns_queries = []
        for log in logs:
            try:
                if log is None or "question" not in log:
                    continue

                question = log.get("question")
                if question is None:
                    continue

                domain_data = question.get("name")
                if not domain_data:
                    continue

                domain = str(domain_data).lower().strip()

                # Basic domain validation (avoid local domains)
                if not domain or domain.endswith(".local") or domain.endswith(".arpa"):
                    continue

                # Avoid duplicates in this polling cycle (deduplication is handled elsewhere too)
                query_key = f"{domain}_{question.get('timestamp', 0)}"
                if query_key in self._processed_domains:
                    continue
                self._processed_domains.add(query_key)

                # Clean up processed domains set periodically
                if len(self._processed_domains) > 5000:
                    self._processed_domains.clear()

                dns_query = DNSQuery(
                    domain=domain,
                    timestamp=datetime.fromtimestamp(question.get("timestamp", 0), UTC),
                    client_ip=str(question.get("client", "")),
                    query_type=str(question.get("type", "A")),
                    blocked=question.get("status") != "NoError",  # Simplified check
                    reason=log.get("reason", "NotFilteredNotFound"),
                    filter_id=log.get("filterId"),
                    rule=log.get("rule") or "",
                    elapsed_ms=log.get("elapsedMs"),
                )
                dns_queries.append(dns_query)

            except Exception as e:
                print(f"Error processing AdGuard log entry: {e}")
                continue

        return dns_queries

    def test_connection(self) -> tuple[bool, str]:
        """
        Test connection to AdGuard.

        Returns:
            tuple[bool, str]: (success, message)
        """
        target_urls = []

        # Add configured URL if available
        if settings.ADGUARD_URL:
            configured_url = f"{settings.ADGUARD_URL}/control/querylog"
            target_urls.append(configured_url)

        # Add fallback URLs
        target_urls.extend(
            [
                "http://adguard:80/control/querylog",
                "http://adguard:3000/control/querylog",
                "http://localhost:80/control/querylog",
            ]
        )

        for url in target_urls:
            try:
                # Skip empty URLs if any
                if "://" not in url:
                    continue

                r = self._session.get(url, timeout=5)

                if r.status_code == 200:
                    return True, f"Connected to AdGuard at {url}"
                elif r.status_code == 401:
                    return False, f"Authentication failed at {url}. Check credentials."
            except requests.exceptions.RequestException as e:
                continue

        return False, "Could not connect to any AdGuard instance"

    @property
    def name(self) -> str:
        return "AdGuard Home"

    @property
    def supported_features(self) -> List[str]:
        return ["query_log", "blocking", "filter_rules"]
