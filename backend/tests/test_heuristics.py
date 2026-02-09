
import pytest
from backend.logic.ml_heuristics import calculate_entropy

def test_entropy_logic():
    # Test sanitization
    assert calculate_entropy("https://www.google.com/") == calculate_entropy("google.com")
    assert calculate_entropy("http://malicious-site.net///") == calculate_entropy("malicious-site.net")
    
    # Test DGA Detection
    dga_score = calculate_entropy("xhk92-z1.ru")
    assert dga_score > 3.5, f"Expected high entropy for DGA, got {dga_score}"
    
    # Test Short vs Long
    short_score = calculate_entropy("a.com")
    long_score = calculate_entropy("this-is-a-very-long-legit-domain-but-with-low-randomness.com")
    assert short_score < 4.0 # Simple domain
    
    # Test Empty
    assert calculate_entropy("") == 0.0

def test_digit_ratio_penalty():
    # Domain with many numbers should have higher score than pure text with same length
    text_only = calculate_entropy("google.com")
    with_numbers = calculate_entropy("g00gl3.com")
    assert with_numbers > text_only
