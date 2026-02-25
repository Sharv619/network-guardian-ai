import re
from typing import Optional
from urllib.parse import urlparse

from ..core.logging_config import get_logger

logger = get_logger(__name__)

MAX_DOMAIN_LENGTH = 253
MAX_LABEL_LENGTH = 63

DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.[A-Za-z0-9-]{1,63}(?<!-))*$",
    re.IGNORECASE,
)

TLD_PATTERN = re.compile(r"^[A-Za-z]{2,63}$")

PUNYCODE_PREFIX = "xn--"


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_domain(
    domain: str,
    max_length: int = MAX_DOMAIN_LENGTH,
    allow_punycode: bool = True,
    strict_tld: bool = False,
) -> str:
    """
    Validate a domain name according to RFC 1035.

    Args:
        domain: The domain name to validate
        max_length: Maximum allowed length (default 253 per RFC 1035)
        allow_punycode: Whether to allow punycode/IDN domains
        strict_tld: Whether to validate TLD format strictly

    Returns:
        The validated and normalized domain name (lowercase)

    Raises:
        ValidationError: If the domain is invalid
    """
    if not domain:
        raise ValidationError("Domain cannot be empty")

    domain = domain.strip().lower()

    if len(domain) > max_length:
        raise ValidationError(f"Domain exceeds maximum length of {max_length} characters")

    if domain.endswith("."):
        domain = domain[:-1]

    if not domain:
        raise ValidationError("Domain cannot be empty after normalization")

    if domain.startswith(".") or domain.endswith("."):
        raise ValidationError("Domain cannot start or end with a dot")

    if ".." in domain:
        raise ValidationError("Domain cannot contain consecutive dots")

    labels = domain.split(".")

    if len(labels) < 2:
        raise ValidationError("Domain must have at least two labels (e.g., example.com)")

    for i, label in enumerate(labels):
        if not label:
            raise ValidationError(f"Empty label at position {i}")

        if len(label) > MAX_LABEL_LENGTH:
            raise ValidationError(f"Label '{label}' exceeds maximum length of {MAX_LABEL_LENGTH}")

        if label.startswith("-") or label.endswith("-"):
            raise ValidationError(f"Label '{label}' cannot start or end with a hyphen")

        if allow_punycode and label.startswith(PUNYCODE_PREFIX):
            try:
                label.encode("ascii").decode("idna")
            except Exception as e:
                raise ValidationError(f"Invalid punycode in label '{label}': {e}")
        else:
            if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", label, re.IGNORECASE):
                raise ValidationError(f"Label '{label}' contains invalid characters")

    tld = labels[-1]
    if strict_tld and not TLD_PATTERN.match(tld):
        raise ValidationError(f"Invalid TLD format: '{tld}'")

    return domain


def validate_domain_safe(domain: str) -> tuple[bool, str]:
    """
    Safely validate a domain without raising exceptions.

    Args:
        domain: The domain name to validate

    Returns:
        Tuple of (is_valid, normalized_domain_or_error_message)
    """
    try:
        normalized = validate_domain(domain)
        return True, normalized
    except ValidationError as e:
        return False, str(e)


def is_valid_domain(domain: str) -> bool:
    """
    Quick check if a domain is valid.

    Args:
        domain: The domain name to validate

    Returns:
        True if valid, False otherwise
    """
    valid, _ = validate_domain_safe(domain)
    return valid


def sanitize_domain(domain: str) -> str:
    """
    Sanitize a domain name by removing unsafe characters.

    Args:
        domain: The domain name to sanitize

    Returns:
        Sanitized domain name
    """
    if not domain:
        return ""

    domain = domain.strip().lower()

    domain = re.sub(r"[^\w\.\-]", "", domain)

    domain = re.sub(r"\.{2,}", ".", domain)

    domain = domain.strip(".")

    return domain


def validate_url(url: str, allowed_schemes: Optional[set[str]] = None) -> str:
    """
    Validate a URL.

    Args:
        url: The URL to validate
        allowed_schemes: Set of allowed schemes (default: http, https)

    Returns:
        The validated URL

    Raises:
        ValidationError: If the URL is invalid
    """
    if not url:
        raise ValidationError("URL cannot be empty")

    allowed_schemes = allowed_schemes or {"http", "https"}

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {e}")

    if parsed.scheme.lower() not in allowed_schemes:
        raise ValidationError(f"URL scheme must be one of: {allowed_schemes}")

    if not parsed.netloc:
        raise ValidationError("URL must have a host")

    validate_domain(parsed.netloc.split(":")[0])

    return url


def validate_ip_address(ip: str) -> str:
    """
    Validate an IP address (IPv4 or IPv6).

    Args:
        ip: The IP address to validate

    Returns:
        The validated IP address

    Raises:
        ValidationError: If the IP address is invalid
    """
    import ipaddress

    if not ip:
        raise ValidationError("IP address cannot be empty")

    try:
        ipaddress.ip_address(ip.strip())
        return ip.strip()
    except ValueError as e:
        raise ValidationError(f"Invalid IP address: {e}")


def validate_request_size(content_length: Optional[int], max_size: int) -> bool:
    """
    Validate request content length.

    Args:
        content_length: The Content-Length header value
        max_size: Maximum allowed size in bytes

    Returns:
        True if valid, False otherwise
    """
    if content_length is None:
        return True

    return content_length <= max_size


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize general text input.

    Args:
        text: The text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    text = text.strip()

    if len(text) > max_length:
        text = text[:max_length]
        logger.warning("Input truncated", extra={"max_length": max_length})

    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text


def escape_sql_like(text: str) -> str:
    """
    Escape special characters for SQL LIKE queries.

    Args:
        text: The text to escape

    Returns:
        Escaped text safe for LIKE queries
    """
    if not text:
        return ""

    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


RESERVED_DOMAINS = {
    "localhost",
    "local",
    "localdomain",
    "broadcasthost",
    "ip6-localhost",
    "ip6-loopback",
    "ip6-localnet",
    "ip6-mcastprefix",
    "ip6-allnodes",
    "ip6-allrouters",
}


def is_reserved_domain(domain: str) -> bool:
    """
    Check if a domain is a reserved/local domain.

    Args:
        domain: The domain to check

    Returns:
        True if reserved, False otherwise
    """
    normalized = domain.lower().strip()

    if normalized in RESERVED_DOMAINS:
        return True

    if normalized.endswith(".local") or normalized.endswith(".localhost"):
        return True

    return False


def should_skip_domain(domain: str) -> bool:
    """
    Determine if a domain should be skipped from analysis.

    Args:
        domain: The domain to check

    Returns:
        True if should skip, False otherwise
    """
    if not is_valid_domain(domain):
        return True

    if is_reserved_domain(domain):
        return True

    skip_tlds = {".arpa", ".local", ".internal", ".localhost"}
    domain_lower = domain.lower()
    if any(domain_lower.endswith(tld) for tld in skip_tlds):
        return True

    return False
