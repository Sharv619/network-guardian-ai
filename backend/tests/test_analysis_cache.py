import pytest
import json
import os
import time

from backend.logic.analysis_cache import (
    AnalysisCache,
    CacheEntry,
    get_cached_analysis,
    cache_analysis_result,
    clear_analysis_cache,
    get_cache_stats,
)


class TestAnalysisCache:
    """Tests for the analysis cache system."""

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a cache with temporary storage."""
        cache_file = os.path.join(temp_cache_dir, "test_cache.json")
        return AnalysisCache(cache_file=cache_file, memory_ttl=60, disk_ttl=300)

    def test_initial_state(self, cache):
        stats = cache.get_stats()
        assert stats["memory_cache_size"] == 0

    def test_set_and_get(self, cache):
        cache.set(
            domain="example.com",
            metadata={"reason": "Blocked"},
            result={"risk_score": "High", "category": "Malware"},
            source="test",
        )

        result = cache.get("example.com", {"reason": "Blocked"})

        assert result is not None
        assert result["risk_score"] == "High"

    def test_get_cache_miss(self, cache):
        result = cache.get("nonexistent.com", {})

        assert result is None

    def test_cache_with_different_metadata(self, cache):
        cache.set(
            domain="example.com",
            metadata={"reason": "Blocked"},
            result={"risk_score": "High"},
            source="test",
        )

        result = cache.get("example.com", {"reason": "Allowed"})

        assert result is None

    def test_cache_ttl_expiry(self, cache):
        short_cache = AnalysisCache(memory_ttl=1, disk_ttl=1)
        short_cache.set(
            domain="ttl-test.com",
            metadata={},
            result={"risk_score": "Medium"},
            source="test",
        )

        time.sleep(2)

        result = short_cache.get("ttl-test.com", {})

        assert result is None

    def test_cache_clear(self, cache):
        cache.set("clear1.com", {}, {"risk_score": "High"}, "test")
        cache.set("clear2.com", {}, {"risk_score": "Low"}, "test")

        cache.clear()

        stats = cache.get_stats()
        assert stats["memory_cache_size"] == 0

    def test_cache_stats(self, cache):
        cache.set("stats1.com", {}, {"risk_score": "High"}, "gemini_ai")
        cache.set("stats2.com", {}, {"risk_score": "Low"}, "local_heuristic")

        stats = cache.get_stats()

        assert stats["memory_cache_size"] == 2
        assert "source_distribution" in stats

    def test_cache_source_distribution(self, cache):
        cache.set("src1.com", {}, {}, "gemini_ai")
        cache.set("src2.com", {}, {}, "gemini_ai")
        cache.set("src3.com", {}, {}, "local_heuristic")

        stats = cache.get_stats()

        assert stats["source_distribution"].get("gemini_ai") == 2
        assert stats["source_distribution"].get("local_heuristic") == 1

    def test_cache_disk_persistence(self, temp_cache_dir):
        cache_file = os.path.join(temp_cache_dir, "persist_cache.json")
        cache1 = AnalysisCache(cache_file=cache_file, disk_ttl=3600)
        cache1.set("persist.com", {}, {"risk_score": "Medium"}, "test")

        del cache1

        cache2 = AnalysisCache(cache_file=cache_file, disk_ttl=3600)
        result = cache2.get("persist.com", {})

        assert result is not None

    def test_cache_update_existing(self, cache):
        cache.set("update.com", {}, {"risk_score": "Low"}, "test")
        cache.set("update.com", {}, {"risk_score": "High"}, "test_updated")

        result = cache.get("update.com", {})

        assert result["risk_score"] == "High"

    def test_public_functions(self, cache):
        cache_analysis_result(
            domain="public.com",
            metadata={"reason": "Test"},
            result={"risk_score": "Medium"},
            source="test",
        )

        result = get_cached_analysis("public.com", {"reason": "Test"})

        assert result is not None

        stats = get_cache_stats()
        assert "memory_cache_size" in stats

        clear_analysis_cache()

    def test_cache_entry_dataclass(self):
        entry = CacheEntry(
            domain="test.com",
            metadata_signature="abc123",
            result={"risk_score": "High"},
            source="test",
            timestamp="2026-02-20T12:00:00Z",
            ttl=60,
        )

        assert entry.domain == "test.com"
        assert entry.source == "test"
        assert entry.ttl == 60

    def test_cache_signature_consistency(self, cache):
        domain = "sig-test.com"
        metadata = {"reason": "Blocked", "filter_id": 2}

        cache.set(domain, metadata, {"risk_score": "High"}, "test")

        result = cache.get(domain, metadata)
        assert result is not None

        result_different = cache.get(domain, {"reason": "Allowed"})
        assert result_different is None

    def test_cache_cleanup_expired(self, cache):
        short_cache = AnalysisCache(memory_ttl=1, disk_ttl=1)

        for i in range(5):
            short_cache.set(f"cleanup{i}.com", {}, {"risk_score": "Low"}, "test")

        time.sleep(2)

        short_cache._cleanup_expired()

        stats = short_cache.get_stats()
        assert stats["valid_memory_entries"] == 0


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_creation(self):
        entry = CacheEntry(
            domain="example.com",
            metadata_signature="sig123",
            result={"risk_score": "High"},
            source="gemini",
            timestamp="2026-02-20T12:00:00Z",
            ttl=300,
        )

        assert entry.domain == "example.com"
        assert entry.metadata_signature == "sig123"
        assert entry.result["risk_score"] == "High"

    def test_entry_default_ttl(self):
        entry = CacheEntry(
            domain="test.com",
            metadata_signature="sig",
            result={},
            source="test",
            timestamp="2026-02-20T12:00:00Z",
            ttl=60,
        )

        assert entry.ttl == 60
