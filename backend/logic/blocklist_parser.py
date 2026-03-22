"""
Blocklist Parser - Parses various DNS blocklist formats into structured data.
Supports: AdGuard DNS Filter, hosts files, EasyList, Steven Black hosts
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

ADGUARD_CATEGORIES = {
    "ads": [
        "advertisement",
        "ads",
        "banner",
        "popup",
        "sponsored",
        "adframe",
        "adclick",
        "adnxs",
        "doubleclick",
        "googlesyndication",
    ],
    "tracking": [
        "analytics",
        "tracking",
        "telemetry",
        "pixel",
        "beacon",
        "计量",
        "统计",
        "分析",
        "track",
        "counter",
    ],
    "malware": [
        "malware",
        "phishing",
        "scam",
        "cryptominer",
        "coinhive",
        "crypto",
        "banking",
        "stealer",
    ],
    "privacy": ["privacy", "surveillance", "spyware", "datalogger", "location", "geo", "gps"],
    "social": [
        "social",
        "facebook",
        "twitter",
        "instagram",
        "socialwidget",
        "share",
        "socialshare",
    ],
    "annoyances": ["annoyance", "cookie", "consent", "notification", "push", "newsletter", "popup"],
    "cryptography": ["crypto", "miner", "coin", "hash", "cryptominer", "webminer"],
    "porn": ["adult", "porn", "xxx", "nude", "erotic", "gambling"],
    "gambling": ["gambling", "casino", "betting", "poker", "lottery", "raffle"],
}

RISK_LEVELS = {
    "ads": "low",
    "tracking": "medium",
    "malware": "high",
    "privacy": "medium",
    "social": "low",
    "annoyances": "low",
    "cryptography": "high",
    "porn": "medium",
    "gambling": "medium",
}


@dataclass
class ParsedBlocklistEntry:
    domain: str
    category: str
    source: str
    rule: str
    risk_level: str
    first_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ParseResult:
    entries: list[ParsedBlocklistEntry]
    skipped: int
    errors: int
    source: str
    raw_line_count: int


class BlocklistParser:
    PATTERNS = {
        "adguard": re.compile(r"\|\|([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9])\^?"),
        "adguard_basic": re.compile(r"\|\|([a-zA-Z0-9\-\.]+[a-zA-Z0-9])\^"),
        "hosts_ipv4": re.compile(r"^0\.0\.0\.0\s+([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9])"),
        "hosts_ipv4_alt": re.compile(r"^127\.0\.0\.1\s+([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9])"),
        "hosts_comment": re.compile(r"^#\s*0\.0\.0\.0\s+([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9])"),
        "easyprivacy": re.compile(r"\|\|([a-zA-Z0-9\-\.]+[a-zA-Z0-9])\^.*\$third-party"),
    }

    SKIP_PREFIXES = ("!", "#", "[", "/", " ", "\n", "\r")
    SKIP_DOMAINS = {
        "localhost",
        "localdomain",
        "broadcasthost",
        "ip6-localhost",
        "ip6-loopback",
        "ip6-localnet",
        "ip6-mcastprefix",
        "ip6-allnodes",
        "ip6-allrouters",
        "ip6-allhosts",
        "0.0.0.0",
        "127.0.0.1",
    }

    def __init__(self, source_name: str = "unknown"):
        self.source_name = source_name

    def parse_line(self, line: str) -> ParsedBlocklistEntry | None:
        line = line.strip()
        if not line or line.startswith(self.SKIP_PREFIXES):
            return None

        domain = None
        rule = line

        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if match:
                domain = match.group(1).lower()
                break

        if not domain:
            return None

        if domain in self.SKIP_DOMAINS or domain.startswith("0.0.0.0"):
            return None

        if len(domain) < 3 or len(domain) > 253:
            return None

        category = self._infer_category(line, domain)
        risk_level = RISK_LEVELS.get(category, "medium")

        return ParsedBlocklistEntry(
            domain=domain,
            category=category,
            source=self.source_name,
            rule=rule[:500],
            risk_level=risk_level,
        )

    def _infer_category(self, line: str, domain: str) -> str:
        line_lower = line.lower()
        domain_lower = domain.lower()
        combined = f"{line_lower} {domain_lower}"

        scores: dict[str, int] = dict.fromkeys(ADGUARD_CATEGORIES, 0)

        for category, keywords in ADGUARD_CATEGORIES.items():
            for keyword in keywords:
                if keyword in combined:
                    scores[category] += 1

        max_score = max(scores.values())
        if max_score > 0:
            for category, score in scores.items():
                if score == max_score:
                    return category

        if any(
            tld in domain_lower for tld in [".tk", ".ml", ".ga", ".cf", ".xyz", ".top", ".loan"]
        ):
            return "malware"

        return "general"

    def parse_content(self, content: str) -> ParseResult:
        entries: list[ParsedBlocklistEntry] = []
        skipped = 0
        errors = 0
        lines = content.split("\n")

        for line in lines:
            try:
                entry = self.parse_line(line)
                if entry:
                    entries.append(entry)
                else:
                    skipped += 1
            except Exception:
                errors += 1

        return ParseResult(
            entries=entries,
            skipped=skipped,
            errors=errors,
            source=self.source_name,
            raw_line_count=len(lines),
        )

    def parse_content_batched(
        self, content: str, batch_size: int = 1000
    ) -> Iterator[list[ParsedBlocklistEntry]]:
        batch: list[ParsedBlocklistEntry] = []

        for line in content.split("\n"):
            try:
                entry = self.parse_line(line)
                if entry:
                    batch.append(entry)
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
            except Exception:
                continue

        if batch:
            yield batch


def parse_adguard_filter(content: str, source_name: str = "adguard_dns") -> ParseResult:
    parser = BlocklistParser(source_name)
    return parser.parse_content(content)


def parse_hosts_file(content: str, source_name: str = "hosts") -> ParseResult:
    parser = BlocklistParser(source_name)
    return parser.parse_content(content)


def parse_easylist(content: str, source_name: str = "easylist") -> ParseResult:
    parser = BlocklistParser(source_name)
    return parser.parse_content(content)


def infer_category_from_domain(domain: str) -> tuple[str, str]:
    domain_lower = domain.lower()
    combined = domain_lower

    scores: dict[str, int] = dict.fromkeys(ADGUARD_CATEGORIES, 0)

    for category, keywords in ADGUARD_CATEGORIES.items():
        for keyword in keywords:
            if keyword in combined:
                scores[category] += 2 if keyword in domain_lower else 1

    tld_risk: dict[str, str] = {
        "tk": "malware",
        "ml": "malware",
        "ga": "malware",
        "cf": "malware",
        "xyz": "malware",
        "top": "malware",
        "loan": "malware",
        "work": "malware",
        "click": "ads",
        "download": "malware",
        "online": "general",
        "website": "general",
        "site": "general",
        "com": "general",
        "net": "general",
        "org": "general",
        "io": "general",
        "co": "general",
    }

    for tld, category in tld_risk.items():
        if domain_lower.endswith(f".{tld}"):
            scores[category] += 5
            break

    max_score = max(scores.values())
    if max_score > 0:
        for category, score in scores.items():
            if score == max_score:
                return category, RISK_LEVELS.get(category, "medium")

    return "general", "medium"
