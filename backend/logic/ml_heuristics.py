import math
import re
from collections import Counter

def sanitize_domain(domain: str) -> str:
    if not domain: return ""
    domain = domain.lower()
    domain = re.sub(r'^https?://', '', domain)
    domain = re.sub(r'^www\.', '', domain)
    domain = re.sub(r'/+$', '', domain)
    parts = domain.split('.')
    return parts[0] if len(parts) > 1 else domain

def calculate_entropy(domain: str) -> float:
    main_part = sanitize_domain(domain)
    if not main_part: return 0.0
    
    probs = [float(main_part.count(c)) / len(main_part) for c in set(main_part)]
    entropy = -sum(p * math.log2(p) for p in probs)
    
    digit_ratio = sum(c.isdigit() for c in main_part) / len(main_part)
    final_score = entropy + (digit_ratio * 2)
    return round(final_score, 2)

def is_dga(domain: str, threshold: float = 3.8) -> bool:
    return calculate_entropy(domain) > threshold

def extract_domain_features(domain: str) -> list:
    main_part = sanitize_domain(domain)
    if not main_part:
        return [0.0, 0, 0.0, 0.0, 0]
    
    length = len(main_part)
    entropy = calculate_entropy(domain)
    digit_ratio = sum(c.isdigit() for c in main_part) / length
    vowel_ratio = sum(c.lower() in 'aeiou' for c in main_part) / length
    non_alphanumeric_count = sum(not c.isalnum() for c in main_part)
    
    return [entropy, length, digit_ratio, vowel_ratio, non_alphanumeric_count]

def is_valid_domain(domain: str) -> bool:
    """
    Checks if a string is a valid domain candidate to prevent data leakage from terminal commands.
    Requires at least one dot and no spaces.
    """
    if not domain or not isinstance(domain, str):
        return False
    # Regex: No spaces, at least one dot
    if re.search(r'\s', domain):
        return False
    if '.' not in domain:
        return False
    return True
