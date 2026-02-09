"""
Analysis Caching System
Caches both local metadata analysis and Gemini API responses to optimize performance
"""

import json
import os
import time
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from ..core.utils import get_iso_timestamp
import hashlib
import threading

@dataclass
class CacheEntry:
    """Represents a cached analysis result"""
    domain: str
    metadata_signature: str
    result: Dict[str, Any]
    source: str  # "metadata", "gemini", "heuristic"
    timestamp: str
    ttl: int  # Time to live in seconds

class AnalysisCache:
    def __init__(self, cache_file: str = "analysis_cache.json", memory_ttl: int = 300, disk_ttl: int = 3600):
        self.cache_file = cache_file
        self.memory_ttl = memory_ttl  # 5 minutes for memory cache
        self.disk_ttl = disk_ttl  # 1 hour for disk cache
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        
        # Load existing cache
        self._load_cache()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _load_cache(self):
        """Load existing cache from disk"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    disk_cache = json.load(f)
                
                # Load into memory cache
                for signature, entry_data in disk_cache.items():
                    try:
                        entry = CacheEntry(**entry_data)
                        if self._is_valid(entry):
                            self.memory_cache[signature] = entry
                    except Exception as e:
                        print(f"Error loading cache entry {signature}: {e}")
                
                print(f"Loaded {len(self.memory_cache)} cache entries from disk")
            except Exception as e:
                print(f"Error loading cache from disk: {e}")
    
    def _start_cleanup_thread(self):
        """Start background thread to clean up expired cache entries"""
        def cleanup():
            while True:
                time.sleep(60)  # Check every minute
                self._cleanup_expired()
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def _generate_signature(self, domain: str, metadata: Dict) -> str:
        """Generate unique signature for domain + metadata combination"""
        metadata_str = json.dumps(metadata, sort_keys=True)
        signature_input = f"{domain}|{metadata_str}"
        return hashlib.md5(signature_input.encode()).hexdigest()
    
    def get(self, domain: str, metadata: Dict) -> Optional[Dict[str, Any]]:
        """Get cached result for domain and metadata"""
        with self.lock:
            signature = self._generate_signature(domain, metadata)
            
            # Check memory cache first
            if signature in self.memory_cache:
                entry = self.memory_cache[signature]
                if self._is_valid(entry):
                    print(f"CACHE HIT (Memory): {domain}")
                    return entry.result
            
            # Check disk cache
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r') as f:
                        disk_cache = json.load(f)
                    
                    if signature in disk_cache:
                        entry_data = disk_cache[signature]
                        entry = CacheEntry(**entry_data)
                        if self._is_valid(entry):
                            print(f"CACHE HIT (Disk): {domain}")
                            # Promote to memory cache
                            self.memory_cache[signature] = entry
                            return entry.result
                except Exception as e:
                    print(f"Error reading disk cache: {e}")
            
            return None
    
    def set(self, domain: str, metadata: Dict, result: Dict[str, Any], source: str, ttl: Optional[int] = None):
        """Store analysis result in cache"""
        with self.lock:
            signature = self._generate_signature(domain, metadata)
            cache_ttl = ttl or self.memory_ttl
            
            entry = CacheEntry(
                domain=domain,
                metadata_signature=signature,
                result=result,
                source=source,
                timestamp=get_iso_timestamp(),
                ttl=cache_ttl
            )
            
            # Store in memory
            self.memory_cache[signature] = entry
            
            # Store in disk (for persistent cache)
            self._save_to_disk(signature, entry)
    
    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid"""
        try:
            entry_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
            expiry_time = entry_time + timedelta(seconds=entry.ttl)
            return datetime.now(timezone.utc) < expiry_time
        except:
            return False
    
    def _save_to_disk(self, signature: str, entry: CacheEntry):
        """Save cache entry to disk"""
        try:
            cache_data = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            
            cache_data[signature] = asdict(entry)
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"Error saving to disk cache: {e}")
    
    def _cleanup_expired(self):
        """Remove expired entries from memory cache"""
        with self.lock:
            current_time = datetime.now(timezone.utc)
            expired_signatures = []
            
            for signature, entry in self.memory_cache.items():
                if not self._is_valid(entry):
                    expired_signatures.append(signature)
            
            for signature in expired_signatures:
                del self.memory_cache[signature]
            
            if expired_signatures:
                print(f"Cleaned up {len(expired_signatures)} expired cache entries")
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.memory_cache.clear()
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            valid_entries = sum(1 for entry in self.memory_cache.values() if self._is_valid(entry))
            
            source_counts = {}
            for entry in self.memory_cache.values():
                if self._is_valid(entry):
                    source = entry.source
                    source_counts[source] = source_counts.get(source, 0) + 1
            
            return {
                "memory_cache_size": len(self.memory_cache),
                "valid_memory_entries": valid_entries,
                "disk_cache_exists": os.path.exists(self.cache_file),
                "source_distribution": source_counts,
                "cache_file_size": os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
            }

# Global cache instance
analysis_cache = AnalysisCache()

def get_cached_analysis(domain: str, metadata: Dict) -> Optional[Dict[str, Any]]:
    """Public function to get cached analysis"""
    return analysis_cache.get(domain, metadata)

def cache_analysis_result(domain: str, metadata: Dict, result: Dict[str, Any], source: str, ttl: Optional[int] = None):
    """Public function to cache analysis result"""
    analysis_cache.set(domain, metadata, result, source, ttl)

def clear_analysis_cache():
    """Public function to clear cache"""
    analysis_cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Public function to get cache statistics"""
    return analysis_cache.get_stats()