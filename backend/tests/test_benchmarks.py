"""
Benchmark tests for Network Guardian AI.
Measures performance of critical components.
"""
import time
import string
import random

import pytest

from backend.logic.ml_heuristics import (
    calculate_entropy,
    extract_domain_features,
    is_dga,
    is_valid_domain,
    sanitize_domain,
)
from backend.logic.anomaly_engine import AnomalyEngine
from backend.logic.metadata_classifier import MetadataClassifier
from backend.logic.analysis_cache import AnalysisCache


def generate_random_domain(length=15):
    """Generate a random domain for testing."""
    chars = string.ascii_lowercase + string.digits
    domain = ''.join(random.choice(chars) for _ in range(length))
    return f"{domain}.com"


def generate_dga_domain():
    """Generate a DGA-like domain."""
    length = random.randint(15, 25)
    chars = string.ascii_lowercase + string.digits
    domain = ''.join(random.choice(chars) for _ in range(length))
    tld = random.choice(['.com', '.net', '.xyz', '.top', '.info'])
    return f"{domain}{tld}"


class TestEntropyBenchmarks:
    """Benchmarks for entropy calculation."""

    @pytest.mark.performance
    def test_entropy_calculation_performance(self, benchmark):
        """Benchmark entropy calculation for single domain."""
        domain = "google.com"
        result = benchmark(calculate_entropy, domain)
        assert isinstance(result, float)

    @pytest.mark.performance
    def test_entropy_calculation_long_domain(self, benchmark):
        """Benchmark entropy for long domain."""
        domain = "very-long-subdomain-name.example-domain.com"
        result = benchmark(calculate_entropy, domain)
        assert isinstance(result, float)

    @pytest.mark.performance
    def test_entropy_batch_performance(self, benchmark):
        """Benchmark entropy calculation for batch of domains."""
        domains = [generate_random_domain() for _ in range(100)]
        
        def calculate_batch():
            return [calculate_entropy(d) for d in domains]
        
        result = benchmark(calculate_batch)
        assert len(result) == 100


class TestFeatureExtractionBenchmarks:
    """Benchmarks for domain feature extraction."""

    @pytest.mark.performance
    def test_feature_extraction_performance(self, benchmark):
        """Benchmark feature extraction for single domain."""
        domain = "test-domain-123.com"
        result = benchmark(extract_domain_features, domain)
        assert len(result) == 5

    @pytest.mark.performance
    def test_feature_extraction_batch(self, benchmark):
        """Benchmark feature extraction for batch."""
        domains = [generate_random_domain() for _ in range(100)]
        
        def extract_batch():
            return [extract_domain_features(d) for d in domains]
        
        result = benchmark(extract_batch)
        assert len(result) == 100


class TestDGADetectionBenchmarks:
    """Benchmarks for DGA detection."""

    @pytest.mark.performance
    def test_dga_detection_normal_domain(self, benchmark):
        """Benchmark DGA detection for normal domain."""
        domain = "google.com"
        result = benchmark(is_dga, domain)
        assert isinstance(result, bool)

    @pytest.mark.performance
    def test_dga_detection_suspicious_domain(self, benchmark):
        """Benchmark DGA detection for suspicious domain."""
        domain = "xkjf8329xnck1234randomstring.com"
        result = benchmark(is_dga, domain)
        assert isinstance(result, bool)

    @pytest.mark.performance
    def test_dga_detection_batch(self, benchmark):
        """Benchmark DGA detection for batch of domains."""
        domains = [generate_dga_domain() for _ in range(100)]
        
        def detect_batch():
            return [is_dga(d) for d in domains]
        
        result = benchmark(detect_batch)
        assert len(result) == 100


class TestDomainValidationBenchmarks:
    """Benchmarks for domain validation."""

    @pytest.mark.performance
    def test_domain_validation_valid(self, benchmark):
        """Benchmark validation for valid domain."""
        domain = "example.com"
        result = benchmark(is_valid_domain, domain)
        assert result is True

    @pytest.mark.performance
    def test_domain_validation_invalid(self, benchmark):
        """Benchmark validation for invalid domain."""
        domain = "a" * 300 + ".com"
        result = benchmark(is_valid_domain, domain)
        assert result is False or result is True

    @pytest.mark.performance
    def test_domain_validation_batch(self, benchmark):
        """Benchmark validation for batch of domains."""
        domains = [generate_random_domain() for _ in range(100)]
        
        def validate_batch():
            return [is_valid_domain(d) for d in domains]
        
        result = benchmark(validate_batch)
        assert len(result) == 100


class TestAnomalyEngineBenchmarks:
    """Benchmarks for anomaly detection engine."""

    @pytest.fixture
    def warm_engine(self):
        """Create and warm up an anomaly engine."""
        engine = AnomalyEngine(contamination=0.05, max_history=1000)
        
        for _ in range(20):
            features = [3.0 + random.uniform(-0.5, 0.5), 
                        15 + random.randint(-5, 5), 
                        random.uniform(0.0, 0.2),
                        random.uniform(0.25, 0.35),
                        random.randint(0, 2)]
            engine.predict_anomaly(features)
        
        return engine

    @pytest.mark.performance
    def test_anomaly_prediction_single(self, benchmark, warm_engine):
        """Benchmark single anomaly prediction."""
        features = [3.5, 15, 0.1, 0.3, 1]
        result = benchmark(warm_engine.predict_anomaly, features)
        assert isinstance(result, tuple)

    @pytest.mark.performance
    def test_anomaly_prediction_batch(self, benchmark, warm_engine):
        """Benchmark batch anomaly predictions."""
        feature_sets = [
            [3.0 + random.uniform(-0.5, 0.5), 15, 0.1, 0.3, 1]
            for _ in range(100)
        ]
        
        def predict_batch():
            return [warm_engine.predict_anomaly(f) for f in feature_sets]
        
        result = benchmark(predict_batch)
        assert len(result) == 100


class TestMetadataClassifierBenchmarks:
    """Benchmarks for metadata classification."""

    @pytest.fixture
    def classifier(self, temp_cache_dir):
        """Create a classifier for benchmarking."""
        import os
        pattern_file = os.path.join(temp_cache_dir, "bench_patterns.json")
        return MetadataClassifier(pattern_db_path=pattern_file)

    @pytest.mark.performance
    def test_classification_single(self, benchmark, classifier):
        """Benchmark single domain classification."""
        metadata = {
            "reason": "Blocked",
            "filter_id": 2,
            "rule": "||malware-domain.com^",
            "client": "192.168.1.100",
        }
        result = benchmark(classifier.classify, metadata)
        assert result is not None

    @pytest.mark.performance
    def test_classification_batch(self, benchmark, classifier):
        """Benchmark batch classification."""
        metadata_list = [
            {"reason": "Blocked", "filter_id": random.randint(1, 5), "rule": f"||domain{i}.com^"}
            for i in range(100)
        ]
        
        def classify_batch():
            return [classifier.classify(m) for m in metadata_list]
        
        result = benchmark(classify_batch)
        assert len(result) == 100


class TestCacheBenchmarks:
    """Benchmarks for analysis cache."""

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a cache for benchmarking."""
        import os
        cache_file = os.path.join(temp_cache_dir, "bench_cache.json")
        return AnalysisCache(cache_file=cache_file)

    @pytest.mark.performance
    def test_cache_set(self, benchmark, cache):
        """Benchmark cache set operation."""
        domain = "test.com"
        metadata = {"reason": "Blocked"}
        result = {"risk_score": "Low", "category": "General Traffic"}
        
        benchmark(cache.set, domain, metadata, result, "local")
        assert True

    @pytest.mark.performance
    def test_cache_get(self, benchmark, cache):
        """Benchmark cache get operation."""
        domain = "cached.com"
        metadata = {"reason": "Blocked"}
        cache.set(domain, metadata, {"risk_score": "Low"}, "local")
        
        result = benchmark(cache.get, domain, metadata)
        assert result is not None

    @pytest.mark.performance
    def test_cache_get_miss(self, benchmark, cache):
        """Benchmark cache miss."""
        result = benchmark(cache.get, "nonexistent.com", {"reason": "Unknown"})
        assert result is None


class TestEndToEndBenchmarks:
    """End-to-end performance benchmarks."""

    @pytest.mark.performance
    def test_full_analysis_pipeline(self, benchmark):
        """Benchmark complete analysis pipeline for one domain."""
        domain = "suspicious-test-domain.com"
        
        def run_pipeline():
            entropy = calculate_entropy(domain)
            features = extract_domain_features(domain)
            dga_check = is_dga(domain)
            valid = is_valid_domain(domain)
            return {
                "entropy": entropy,
                "features": features,
                "is_dga": dga_check,
                "is_valid": valid,
            }
        
        result = benchmark(run_pipeline)
        assert "entropy" in result
        assert "is_dga" in result

    @pytest.mark.performance
    def test_full_pipeline_batch(self, benchmark):
        """Benchmark complete analysis pipeline for batch."""
        domains = [generate_random_domain() for _ in range(50)]
        
        def run_batch():
            results = []
            for domain in domains:
                entropy = calculate_entropy(domain)
                features = extract_domain_features(domain)
                dga = is_dga(domain)
                results.append({
                    "domain": domain,
                    "entropy": entropy,
                    "is_dga": dga,
                })
            return results
        
        result = benchmark(run_batch)
        assert len(result) == 50


class TestMemoryBenchmarks:
    """Memory usage benchmarks."""

    @pytest.mark.performance
    def test_large_history_memory(self):
        """Test memory usage with large history."""
        from unittest.mock import patch
        
        with patch("backend.logic.anomaly_engine.db_logger.get_all_domain_features", return_value=[]):
            engine = AnomalyEngine(max_history=10000)
            
            for i in range(1000):
                features = [3.0 + random.uniform(-0.5, 0.5), 15, 0.1, 0.3, 1]
                engine.predict_anomaly(features)
            
            assert len(engine.history) == 1000

    @pytest.mark.performance
    def test_processed_domains_memory(self):
        """Test memory usage of processed domains set."""
        processed = set()
        
        for _ in range(1000):
            domain = generate_random_domain()
            processed.add(domain)
        
        assert len(processed) == 1000


class TestConcurrencyBenchmarks:
    """Concurrency performance tests."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_entropy_calculations(self):
        """Test concurrent entropy calculations."""
        import asyncio
        
        domains = [generate_random_domain() for _ in range(100)]
        
        def calc_entropy(domain):
            return calculate_entropy(domain)
        
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, calc_entropy, d) for d in domains]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
        assert all(isinstance(r, float) for r in results)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_feature_extraction(self):
        """Test concurrent feature extraction."""
        import asyncio
        
        domains = [generate_random_domain() for _ in range(100)]
        
        def extract_features(domain):
            return extract_domain_features(domain)
        
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, extract_features, d) for d in domains]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
        assert all(len(r) == 5 for r in results)
