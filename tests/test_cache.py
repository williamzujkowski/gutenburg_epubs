"""Tests for the caching module."""

import json
import time
from pathlib import Path

import pytest

from gutenberg_downloader.cache import APICache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def api_cache(temp_cache_dir):
    """Create an APICache instance with a temporary directory."""
    return APICache(cache_dir=str(temp_cache_dir))


@pytest.fixture
def sample_data():
    """Sample data for caching tests."""
    return {
        "count": 1,
        "results": [
            {
                "id": 1342,
                "title": "Pride and Prejudice",
                "authors": [
                    {
                        "name": "Austen, Jane",
                        "birth_year": 1775,
                        "death_year": 1817
                    }
                ]
            }
        ]
    }


class TestAPICache:
    """Tests for the APICache class."""

    def test_init(self, temp_cache_dir):
        """Test cache initialization."""
        api_cache = APICache(cache_dir=str(temp_cache_dir), ttl_hours=48)
        assert api_cache.cache_dir == temp_cache_dir
        assert api_cache.ttl_hours == 48

    def test_get_cache_path(self, api_cache):
        """Test _get_cache_path method."""
        key = "books?search=pride&languages=en"
        path = api_cache._get_cache_path(key)
        assert path == api_cache.cache_dir / "books_search=pride&languages=en.json"

    def test_is_expired(self, api_cache):
        """Test _is_expired method."""
        # Not expired - current time
        assert not api_cache._is_expired(time.time())
        
        # Expired - 25 hours ago (default TTL is 24 hours)
        assert api_cache._is_expired(time.time() - (25 * 3600))
        
        # Custom TTL
        api_cache.ttl_hours = 1
        assert api_cache._is_expired(time.time() - (2 * 3600))

    def test_get_not_found(self, api_cache):
        """Test get method when key not found."""
        result = api_cache.get("nonexistent-key")
        assert result is None

    def test_set_and_get(self, api_cache, sample_data):
        """Test set and get methods."""
        key = "books/1342"
        api_cache.set(key, sample_data)
        
        # Verify file was created
        cache_path = api_cache._get_cache_path(key)
        assert cache_path.exists()
        
        # Get the cached data
        result = api_cache.get(key)
        assert result == sample_data
    
    def test_get_expired(self, api_cache, sample_data, monkeypatch):
        """Test get method with expired entry."""
        key = "books/expired"
        
        # Set cache entry
        api_cache.set(key, sample_data)
        
        # Modify file timestamp to make it appear old
        cache_path = api_cache._get_cache_path(key)
        cache_data = json.loads(cache_path.read_text())
        cache_data["timestamp"] = time.time() - (api_cache.ttl_hours * 3600 + 60)  # Older than TTL
        cache_path.write_text(json.dumps(cache_data))
        
        # Get should return None for expired entry
        result = api_cache.get(key)
        assert result is None

    def test_clear(self, api_cache, sample_data):
        """Test clear method."""
        # Add multiple entries
        api_cache.set("key1", sample_data)
        api_cache.set("key2", {"other": "data"})
        
        # Verify files exist
        assert api_cache._get_cache_path("key1").exists()
        assert api_cache._get_cache_path("key2").exists()
        
        # Clear cache
        api_cache.clear()
        
        # Verify files are gone
        assert not api_cache._get_cache_path("key1").exists()
        assert not api_cache._get_cache_path("key2").exists()

    def test_invalid_json(self, api_cache, sample_data):
        """Test handling of invalid JSON in cache file."""
        key = "invalid-json"
        cache_path = api_cache._get_cache_path(key)
        
        # Create a cache file with invalid JSON
        cache_path.write_text("This is not valid JSON")
        
        # Get should return None and not crash
        result = api_cache.get(key)
        assert result is None


class TestCacheIntegration:
    """Integration tests for the cache module."""
    
    def test_multiple_gets_and_sets(self, api_cache):
        """Test multiple operations on the cache."""
        # Set multiple entries
        api_cache.set("key1", {"data": "value1"})
        api_cache.set("key2", {"data": "value2"})
        api_cache.set("key3", {"data": "value3"})
        
        # Get the entries
        assert api_cache.get("key1") == {"data": "value1"}
        assert api_cache.get("key2") == {"data": "value2"}
        assert api_cache.get("key3") == {"data": "value3"}
        
        # Update an entry
        api_cache.set("key2", {"data": "updated"})
        assert api_cache.get("key2") == {"data": "updated"}
        
        # Delete an entry
        api_cache._get_cache_path("key3").unlink()
        assert api_cache.get("key3") is None