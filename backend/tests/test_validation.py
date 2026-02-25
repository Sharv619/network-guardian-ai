import pytest
from datetime import datetime

from backend.core.validators import (
    validate_domain,
    validate_domain_safe,
    is_valid_domain,
    sanitize_domain,
    validate_url,
    validate_ip_address,
    sanitize_input,
    is_reserved_domain,
    should_skip_domain,
    ValidationError,
)
from backend.core.rate_limiter import RateLimiter, MultiRateLimiter, IPReputationTracker


class TestDomainValidation:
    """Tests for domain validation functions."""

    def test_valid_domain_simple(self):
        assert validate_domain("example.com") == "example.com"
        assert validate_domain("google.com") == "google.com"
        assert validate_domain("sub.domain.com") == "sub.domain.com"

    def test_valid_domain_uppercase(self):
        result = validate_domain("EXAMPLE.COM")
        assert result == "example.com"

    def test_valid_domain_trailing_dot(self):
        result = validate_domain("example.com.")
        assert result == "example.com"

    def test_valid_domain_with_numbers(self):
        assert validate_domain("test123.com") == "test123.com"
        assert validate_domain("123test.net") == "123test.net"

    def test_invalid_domain_empty(self):
        with pytest.raises(ValidationError):
            validate_domain("")

    def test_invalid_domain_too_long(self):
        long_domain = "a" * 250 + ".com"
        with pytest.raises(ValidationError):
            validate_domain(long_domain)

    def test_invalid_domain_single_label(self):
        with pytest.raises(ValidationError):
            validate_domain("localhost")

    def test_invalid_domain_consecutive_dots(self):
        with pytest.raises(ValidationError):
            validate_domain("example..com")

    def test_invalid_domain_starts_with_dot(self):
        with pytest.raises(ValidationError):
            validate_domain(".example.com")

    def test_invalid_domain_label_starts_with_hyphen(self):
        with pytest.raises(ValidationError):
            validate_domain("-example.com")

    def test_validate_domain_safe_valid(self):
        valid, result = validate_domain_safe("example.com")
        assert valid is True
        assert result == "example.com"

    def test_validate_domain_safe_invalid(self):
        valid, error = validate_domain_safe("invalid..domain")
        assert valid is False
        assert "consecutive" in error.lower()

    def test_is_valid_domain(self):
        assert is_valid_domain("example.com") is True
        assert is_valid_domain("") is False
        assert is_valid_domain("invalid..domain") is False

    def test_sanitize_domain(self):
        assert sanitize_domain("  EXAMPLE.COM  ") == "example.com"
        assert sanitize_domain("test..domain") == "test.domain"
        assert sanitize_domain("") == ""


class TestURLValidation:
    """Tests for URL validation functions."""

    def test_valid_http_url(self):
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_valid_https_url(self):
        result = validate_url("https://example.com/path")
        assert result == "https://example.com/path"

    def test_invalid_url_scheme(self):
        with pytest.raises(ValidationError):
            validate_url("ftp://example.com")

    def test_invalid_url_no_host(self):
        with pytest.raises(ValidationError):
            validate_url("http://")


class TestIPAddressValidation:
    """Tests for IP address validation functions."""

    def test_valid_ipv4(self):
        assert validate_ip_address("192.168.1.1") == "192.168.1.1"
        assert validate_ip_address("8.8.8.8") == "8.8.8.8"

    def test_valid_ipv6(self):
        assert validate_ip_address("::1") == "::1"
        assert validate_ip_address("2001:db8::1") == "2001:db8::1"

    def test_invalid_ip(self):
        with pytest.raises(ValidationError):
            validate_ip_address("256.256.256.256")


class TestReservedDomains:
    """Tests for reserved domain detection."""

    def test_is_reserved_domain(self):
        assert is_reserved_domain("localhost") is True
        assert is_reserved_domain("test.local") is True
        assert is_reserved_domain("example.localhost") is True
        assert is_reserved_domain("example.com") is False

    def test_should_skip_domain(self):
        assert should_skip_domain("test.local") is True
        assert should_skip_domain("test.arpa") is True
        assert should_skip_domain("example.com") is False


class TestInputSanitization:
    """Tests for input sanitization."""

    def test_sanitize_input_strip(self):
        assert sanitize_input("  test  ") == "test"

    def test_sanitize_input_max_length(self):
        long_text = "a" * 20000
        result = sanitize_input(long_text, max_length=1000)
        assert len(result) == 1000

    def test_sanitize_input_control_chars(self):
        assert sanitize_input("test\x00\x01") == "test"


class TestRateLimiter:
    """Tests for rate limiting functionality."""

    def test_allows_under_limit(self):
        limiter = RateLimiter(limit=5, window=60, prefix="test")
        
        for i in range(5):
            assert limiter.is_allowed("user1") is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(limit=3, window=60, prefix="test")
        
        for i in range(3):
            limiter.is_allowed("user1")
        
        assert limiter.is_allowed("user1") is False

    def test_different_keys_independent(self):
        limiter = RateLimiter(limit=2, window=60, prefix="test")
        
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False
        
        assert limiter.is_allowed("user2") is True

    def test_burst_allowance(self):
        limiter = RateLimiter(limit=3, window=60, burst=2, prefix="test")
        
        for i in range(5):
            assert limiter.is_allowed("user1") is True
        
        assert limiter.is_allowed("user1") is False

    def test_get_remaining(self):
        limiter = RateLimiter(limit=5, window=60, prefix="test")
        
        assert limiter.get_remaining("user1") == 5
        
        limiter.is_allowed("user1")
        assert limiter.get_remaining("user1") == 4

    def test_block_function(self):
        limiter = RateLimiter(limit=5, window=60, prefix="test")
        limiter.is_allowed("user1")
        
        limiter.block("user1", 10)
        assert limiter.is_allowed("user1") is False

    def test_clear_single_identifier(self):
        limiter = RateLimiter(limit=2, window=60, prefix="test")
        
        limiter.is_allowed("user1")
        limiter.is_allowed("user2")
        
        limiter.clear("user1")
        
        assert limiter.get_remaining("user1") == 2
        assert limiter.get_remaining("user2") == 1


class TestMultiRateLimiter:
    """Tests for multi-rate limiter."""

    def test_register_and_check(self):
        multi = MultiRateLimiter()
        multi.register("api", limit=5, window=60)
        
        assert multi.is_allowed("api", "user1") is True
        assert multi.is_allowed("unknown", "user1") is True

    def test_multiple_limiters_independent(self):
        multi = MultiRateLimiter()
        multi.register("limiter1", limit=2, window=60)
        multi.register("limiter2", limit=5, window=60)
        
        multi.is_allowed("limiter1", "user1")
        multi.is_allowed("limiter1", "user1")
        
        assert multi.is_allowed("limiter1", "user1") is False
        assert multi.is_allowed("limiter2", "user1") is True


class TestIPReputationTracker:
    """Tests for IP reputation tracking."""

    def test_initial_score(self):
        tracker = IPReputationTracker(initial_score=0)
        assert tracker.get_score("192.168.1.1") == 0

    def test_successful_requests_increase_score(self):
        tracker = IPReputationTracker(initial_score=0)
        
        tracker.record_request("192.168.1.1", success=True)
        assert tracker.get_score("192.168.1.1") == 1

    def test_failed_requests_decrease_score(self):
        tracker = IPReputationTracker(initial_score=0)
        
        tracker.record_request("192.168.1.1", success=False)
        assert tracker.get_score("192.168.1.1") == -5

    def test_block_threshold(self):
        tracker = IPReputationTracker(initial_score=0, block_threshold=-10)
        
        for i in range(3):
            tracker.record_request("192.168.1.1", success=False)
        
        assert tracker.is_blocked("192.168.1.1") is True

    def test_manual_block(self):
        tracker = IPReputationTracker()
        
        tracker.block_ip("192.168.1.1", reason="test")
        
        assert tracker.is_blocked("192.168.1.1") is True

    def test_manual_unblock(self):
        tracker = IPReputationTracker()
        
        tracker.block_ip("192.168.1.1", reason="test")
        tracker.unblock_ip("192.168.1.1")
        
        assert tracker.is_blocked("192.168.1.1") is False

    def test_malicious_activity(self):
        tracker = IPReputationTracker(initial_score=0)
        
        tracker.record_malicious_activity("192.168.1.1", severity=20)
        
        assert tracker.get_score("192.168.1.1") == -20

    def test_stats(self):
        tracker = IPReputationTracker()
        
        tracker.record_request("192.168.1.1", success=True)
        tracker.record_request("192.168.1.2", success=False)
        tracker.block_ip("192.168.1.3")
        
        stats = tracker.get_stats()
        
        assert stats["total_ips_tracked"] == 3
        assert stats["blocked_ips"] == 1
