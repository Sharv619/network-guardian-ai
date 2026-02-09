import pytest
from backend.logic.ml_heuristics import calculate_entropy, sanitize_domain

def test_sanitize_domain():
    """Tests that sanitize_domain correctly strips prefixes and suffixes."""
    assert sanitize_domain("https://www.google.com/") == "google"
    assert sanitize_domain("http://malicious-site.net///") == "malicious-site"
    assert sanitize_domain("google.com") == "google"
    assert sanitize_domain("www.sub.domain.co.uk") == "www"

def test_entropy_logic():
    """Tests the entropy calculation for different types of domains."""
    # Test sanitization (indirectly)
    assert calculate_entropy("https://www.google.com/") == calculate_entropy("google.com")

    # Test legitimate domain (low entropy)
    google_score = calculate_entropy("google.com")
    assert google_score < 3.0, f"Expected low entropy for google.com, got {google_score}"

    # Test DGA-like domain (high entropy)
    dga_score = calculate_entropy("xhk92-z1.ru")
    assert dga_score > 3.5, f"Expected high entropy for DGA, got {dga_score}"

    # Test empty and short domains
    assert calculate_entropy("") == 0.0
    short_score = calculate_entropy("a.com")
    assert short_score < 4.0  # Simple domain, should have reasonable entropy

def test_digit_ratio_penalty():
    """Tests that domains with digits have a higher entropy score."""
    # Domain with many numbers should have higher score than pure text with same length
    text_only = calculate_entropy("googlecom")
    with_numbers = calculate_entropy("g00glec0m")
    assert with_numbers > text_only