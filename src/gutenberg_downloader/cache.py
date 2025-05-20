"""Caching module for API responses and metadata."""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class APICache:
    """Simple file-based cache for API responses."""
    
    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        """Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time to live for cache entries in hours
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"Initialized API cache at {cache_dir} with TTL {ttl_hours} hours")
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the cache file path for a key."""
        # Clean the key to be filesystem-safe
        safe_key = key.replace("/", "_").replace(":", "").replace("?", "_")
        return self.cache_dir / f"{safe_key}.json"
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if a cache entry is expired."""
        age_hours = (time.time() - timestamp) / 3600
        return age_hours > self.ttl_hours
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            if self._is_expired(cache_data['timestamp']):
                logger.debug(f"Cache expired for key: {key}")
                cache_path.unlink()
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return cache_data['value']
            
        except Exception as e:
            logger.error(f"Error reading cache for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successful
        """
        cache_path = self._get_cache_path(key)
        cache_data = {
            'timestamp': time.time(),
            'value': value
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            logger.debug(f"Cached value for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error writing cache for key {key}: {e}")
            return False
    
    def clear(self, older_than_hours: Optional[int] = None):
        """Clear cache entries.
        
        Args:
            older_than_hours: Only clear entries older than this many hours
        """
        cleared = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if older_than_hours:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    age_hours = (time.time() - cache_data['timestamp']) / 3600
                    if age_hours <= older_than_hours:
                        continue
                
                cache_file.unlink()
                cleared += 1
                
            except Exception as e:
                logger.error(f"Error clearing cache file {cache_file}: {e}")
        
        logger.info(f"Cleared {cleared} cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'total_entries': 0,
            'expired_entries': 0,
            'total_size_bytes': 0,
            'oldest_entry': None,
            'newest_entry': None
        }
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                stats['total_entries'] += 1
                stats['total_size_bytes'] += cache_file.stat().st_size
                
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                timestamp = cache_data['timestamp']
                
                if self._is_expired(timestamp):
                    stats['expired_entries'] += 1
                
                if stats['oldest_entry'] is None or timestamp < stats['oldest_entry']:
                    stats['oldest_entry'] = timestamp
                
                if stats['newest_entry'] is None or timestamp > stats['newest_entry']:
                    stats['newest_entry'] = timestamp
                    
            except Exception:
                pass
        
        # Convert timestamps to datetime strings
        if stats['oldest_entry']:
            stats['oldest_entry'] = datetime.fromtimestamp(stats['oldest_entry']).isoformat()
        if stats['newest_entry']:
            stats['newest_entry'] = datetime.fromtimestamp(stats['newest_entry']).isoformat()
        
        return stats


class InMemoryCache:
    """In-memory cache for frequently accessed data."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """Initialize the in-memory cache.
        
        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time to live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        logger.info(f"Initialized in-memory cache with max size {max_size}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if time.time() - entry['timestamp'] > self.ttl_seconds:
            del self.cache[key]
            del self.access_times[key]
            return None
        
        self.access_times[key] = time.time()
        return entry['value']
    
    def set(self, key: str, value: Any):
        """Set a value in the cache."""
        # Remove oldest entries if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        self.access_times[key] = time.time()
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()