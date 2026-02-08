
import math
from collections import Counter

def calculate_entropy(domain: str) -> float:
    if not domain: return 0.0
    
    # Clean the domain (remove TLD)
    parts = domain.split('.')
    main_part = parts[0] if len(parts) > 1 else domain
    
    # Correct Shannon Entropy (Base 2)
    if not main_part: return 0.0
    probs = [float(main_part.count(c)) / len(main_part) for c in set(main_part)]
    entropy = -sum(p * math.log2(p) for p in probs)
    
    # SRE 'Extra Signal': Malicious domains often mix numbers and letters
    digit_ratio = sum(c.isdigit() for c in main_part) / len(main_part)
    
    # Weighted Score: Entropy + penalty for numbers
    # DGA domains like 'x837df2.com' will have both high entropy and high digit ratio
    final_score = entropy + (digit_ratio * 2)
    return round(final_score, 2)

def is_dga(domain: str, threshold: float = 3.8) -> bool: # 4.0 might be too high for short strings
    return calculate_entropy(domain) > threshold
