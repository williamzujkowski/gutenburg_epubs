"""Tests for the MirrorManager class."""

import json
import os
import time
from pathlib import Path
import pytest
from unittest.mock import patch, Mock, MagicMock

import httpx

from gutenberg_downloader.mirror_manager import MirrorManager, MirrorSite
from gutenberg_downloader.constants import BASE_URL


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory for tests."""
    config_dir = tmp_path / "test_config"
    config_dir.mkdir()
    return str(config_dir)


@pytest.fixture
def mirror_site():
    """Create a test mirror site."""
    return MirrorSite(
        name="Test Mirror",
        base_url="https://test-mirror.org/",
        priority=3,
        country="US",
        active=True,
        health_score=1.0
    )


@pytest.fixture
def mock_response():
    """Create a mock response fixture."""
    mock = Mock()
    mock.status_code = 200
    return mock


class TestMirrorSite:
    """Tests for the MirrorSite dataclass."""

    def test_init(self):
        """Test MirrorSite initialization."""
        mirror = MirrorSite(
            name="Test Mirror",
            base_url="https://test-mirror.org/",
            priority=3,
            country="US"
        )
        
        assert mirror.name == "Test Mirror"
        assert mirror.base_url == "https://test-mirror.org/"
        assert mirror.priority == 3
        assert mirror.country == "US"
        assert mirror.active is True  # Default
        assert mirror.health_score == 1.0  # Default
        assert mirror.last_checked is None  # Default
        assert mirror.last_success is None  # Default


class TestMirrorManager:
    """Tests for the MirrorManager class."""

    def test_init(self, temp_config_dir):
        """Test MirrorManager initialization."""
        manager = MirrorManager(config_dir=temp_config_dir)
        
        assert manager.config_dir == temp_config_dir
        assert manager.primary_site == BASE_URL
        assert manager.mirrors_file == os.path.join(temp_config_dir, "mirrors.json")
        assert isinstance(manager.mirrors, list)
        assert len(manager.mirrors) > 0  # Should have default mirrors
        assert isinstance(manager.client, httpx.Client)
        assert isinstance(manager.recently_used, list)
        assert isinstance(manager.failure_counts, dict)
        assert isinstance(manager.book_availability, dict)

    def test_context_manager(self, temp_config_dir):
        """Test MirrorManager as a context manager."""
        with patch('gutenberg_downloader.mirror_manager.httpx.Client') as mock_client:
            with MirrorManager(config_dir=temp_config_dir) as manager:
                pass
            mock_client.return_value.close.assert_called_once()

    def test_load_mirrors_non_existent(self, temp_config_dir):
        """Test loading mirrors when file doesn't exist."""
        manager = MirrorManager(config_dir=temp_config_dir)
        # File shouldn't exist yet
        assert not os.path.exists(manager.mirrors_file)
        
        # Should use default mirrors
        assert len(manager.mirrors) > 0
        # First mirror should be the primary site
        assert any(m.base_url == BASE_URL for m in manager.mirrors)

    def test_save_and_load_mirrors(self, temp_config_dir):
        """Test saving and loading mirrors."""
        # Create a manager with default mirrors
        manager1 = MirrorManager(config_dir=temp_config_dir)
        original_mirrors = len(manager1.mirrors)
        
        # Add a new mirror
        manager1.add_mirror(
            name="Test Mirror", 
            base_url="https://test-mirror.example.org/", 
            priority=5, 
            country="TS"
        )
        
        # Save mirrors
        assert manager1.save_mirrors() is True
        assert os.path.exists(manager1.mirrors_file)
        
        # Create a new manager instance that should load from the file
        manager2 = MirrorManager(config_dir=temp_config_dir)
        
        # Check if our test mirror was loaded
        assert len(manager2.mirrors) == original_mirrors + 1
        test_mirror = next((m for m in manager2.mirrors if m.name == "Test Mirror"), None)
        assert test_mirror is not None
        assert test_mirror.base_url == "https://test-mirror.example.org/"
        assert test_mirror.priority == 5
        assert test_mirror.country == "TS"

    def test_normalize_base_url(self, temp_config_dir):
        """Test URL normalization."""
        manager = MirrorManager(config_dir=temp_config_dir)
        
        # Test adding trailing slash
        assert manager._normalize_base_url("https://example.org") == "https://example.org/"
        
        # Test keeping existing trailing slash
        assert manager._normalize_base_url("https://example.org/") == "https://example.org/"
        
        # Test upgrading http to https
        assert manager._normalize_base_url("http://example.org") == "https://example.org/"
        
        # Test not upgrading for specific domains that don't support HTTPS
        assert manager._normalize_base_url("http://mirrors.xmission.com") == "https://mirrors.xmission.com/"
        assert manager._normalize_base_url("http://www.mirrorservice.org") == "https://www.mirrorservice.org/"
        # Special domains that explicitly don't support HTTPS
        assert manager._normalize_base_url("http://eremita.di.uminho.pt") == "http://eremita.di.uminho.pt/"
        assert manager._normalize_base_url("http://mirror.csclub.uwaterloo.ca") == "http://mirror.csclub.uwaterloo.ca/"

    def test_add_mirror(self, temp_config_dir):
        """Test adding a mirror."""
        manager = MirrorManager(config_dir=temp_config_dir)
        initial_count = len(manager.mirrors)
        
        # Add a new mirror
        manager.add_mirror(
            name="New Test Mirror", 
            base_url="https://new-test.example.org", 
            priority=4, 
            country="TS"
        )
        
        # Check if mirror was added
        assert len(manager.mirrors) == initial_count + 1
        new_mirror = next((m for m in manager.mirrors if m.name == "New Test Mirror"), None)
        assert new_mirror is not None
        assert new_mirror.base_url == "https://new-test.example.org/"  # Note trailing slash added
        assert new_mirror.priority == 4
        assert new_mirror.country == "TS"
        assert new_mirror.active is True
        assert new_mirror.health_score == 1.0
        
        # Add the same mirror with different info (should update)
        manager.add_mirror(
            name="Updated Mirror", 
            base_url="https://new-test.example.org", 
            priority=5, 
            country="US"
        )
        
        # Check if mirror was updated (count should remain the same)
        assert len(manager.mirrors) == initial_count + 1
        updated_mirror = next((m for m in manager.mirrors if m.base_url == "https://new-test.example.org/"), None)
        assert updated_mirror is not None
        assert updated_mirror.name == "Updated Mirror"
        assert updated_mirror.priority == 5
        assert updated_mirror.country == "US"

    def test_remove_mirror(self, temp_config_dir):
        """Test removing a mirror."""
        manager = MirrorManager(config_dir=temp_config_dir)
        initial_count = len(manager.mirrors)
        
        # Add a mirror to remove
        test_url = "https://to-be-removed.example.org/"
        manager.add_mirror(
            name="To Be Removed", 
            base_url=test_url, 
            priority=3, 
            country="RM"
        )
        
        # Add to recently used
        manager.recently_used.append(test_url)
        # Add failure count
        manager.failure_counts[test_url] = 2
        
        # Remove the mirror
        manager.remove_mirror(test_url)
        
        # Check if mirror was removed
        assert len(manager.mirrors) == initial_count
        assert not any(m.base_url == test_url for m in manager.mirrors)
        assert test_url not in manager.recently_used
        assert test_url not in manager.failure_counts

    def test_get_mirrors(self, temp_config_dir):
        """Test getting all mirrors."""
        manager = MirrorManager(config_dir=temp_config_dir)
        mirrors = manager.get_mirrors()
        
        # Should return a copy, not the original list
        assert mirrors is not manager.mirrors
        assert len(mirrors) == len(manager.mirrors)
        
        # Modifying the returned list shouldn't affect the original
        mirrors.pop()
        assert len(mirrors) != len(manager.mirrors)

    def test_get_active_mirrors(self, temp_config_dir):
        """Test getting only active mirrors."""
        manager = MirrorManager(config_dir=temp_config_dir)
        
        # Add an active and inactive mirror
        manager.add_mirror(
            name="Active Mirror", 
            base_url="https://active.example.org/", 
            priority=3
        )
        manager.add_mirror(
            name="Inactive Mirror", 
            base_url="https://inactive.example.org/", 
            priority=3
        )
        
        # Set one mirror inactive
        inactive_index = next(i for i, m in enumerate(manager.mirrors) 
                            if m.base_url == "https://inactive.example.org/")
        manager.mirrors[inactive_index].active = False
        
        # Get active mirrors
        active_mirrors = manager.get_active_mirrors()
        
        # Check only active mirrors are returned
        assert all(m.active for m in active_mirrors)
        assert any(m.base_url == "https://active.example.org/" for m in active_mirrors)
        assert not any(m.base_url == "https://inactive.example.org/" for m in active_mirrors)

    def test_build_book_url(self, temp_config_dir):
        """Test building book URLs for different mirrors."""
        manager = MirrorManager(config_dir=temp_config_dir)
        book_id = 1234
        
        # Test standard Gutenberg URL
        assert manager.build_book_url(book_id, BASE_URL) == f"{BASE_URL}ebooks/{book_id}.epub"
        
        # Test PGLAF URL
        pglaf_url = "https://gutenberg.pglaf.org/"
        assert manager.build_book_url(book_id, pglaf_url) == f"{pglaf_url}cache/epub/{book_id}/pg{book_id}.epub"
        
        # Test Nabasny URL
        nabasny_url = "https://gutenberg.nabasny.com/"
        assert manager.build_book_url(book_id, nabasny_url) == f"{nabasny_url}ebooks/{book_id}.epub3.images"
        
        # Test xmission URL
        xmission_url = "https://mirrors.xmission.com/gutenberg/"
        assert manager.build_book_url(book_id, xmission_url) == f"{xmission_url}cache/epub/{book_id}/pg{book_id}.epub"
        
        # Test UK Mirror Service URL
        uk_mirror_url = "https://www.mirrorservice.org/sites/ftp.ibiblio.org/pub/docs/books/gutenberg/"
        assert manager.build_book_url(book_id, uk_mirror_url) == f"{uk_mirror_url}{book_id}/pg{book_id}.epub"
        
        # Test generic fallback
        generic_url = "https://generic.example.org/"
        assert manager.build_book_url(book_id, generic_url) == f"{generic_url}cache/epub/{book_id}/pg{book_id}.epub"

    def test_select_mirror(self, temp_config_dir):
        """Test mirror selection algorithm."""
        manager = MirrorManager(config_dir=temp_config_dir)
        
        # Add some test mirrors
        manager.add_mirror(
            name="High Priority", 
            base_url="https://high.example.org/", 
            priority=5
        )
        manager.add_mirror(
            name="Medium Priority", 
            base_url="https://medium.example.org/", 
            priority=3
        )
        manager.add_mirror(
            name="Low Priority", 
            base_url="https://low.example.org/", 
            priority=1
        )
        
        # Test basic selection
        selected_url = manager.select_mirror()
        assert selected_url in [m.base_url for m in manager.mirrors]
        
        # Test that URL was added to recently used
        assert selected_url in manager.recently_used
        
        # Test selection with book availability
        book_id = 1234
        manager.book_availability[book_id] = {"https://high.example.org/"}
        selected_url = manager.select_mirror(book_id)
        assert selected_url == "https://high.example.org/"
        
        # Test fallback to other mirrors if none available
        manager.mirrors = []  # No mirrors available
        fallback_url = manager.select_mirror()
        assert fallback_url == manager.primary_site

    def test_report_failure(self, temp_config_dir):
        """Test reporting mirror failures."""
        manager = MirrorManager(config_dir=temp_config_dir)
        
        # Add test mirror
        test_url = "https://test.example.org/"
        manager.add_mirror(
            name="Test Mirror", 
            base_url=test_url, 
            priority=3
        )
        
        # Initial state
        mirror_index = next(i for i, m in enumerate(manager.mirrors) if m.base_url == test_url)
        initial_health = manager.mirrors[mirror_index].health_score
        assert manager.mirrors[mirror_index].active is True
        assert manager.failure_counts[test_url] == 0
        
        # Report a failure
        manager.report_failure(test_url)
        
        # Check effects
        assert manager.failure_counts[test_url] == 1
        assert manager.mirrors[mirror_index].health_score < initial_health
        assert manager.mirrors[mirror_index].active is True  # Still active after one failure
        
        # Report multiple failures
        for _ in range(3):
            manager.report_failure(test_url)
            
        # Should be inactive after multiple failures
        assert manager.failure_counts[test_url] > 3
        assert manager.mirrors[mirror_index].health_score < initial_health
        assert manager.mirrors[mirror_index].active is False

    def test_report_success(self, temp_config_dir):
        """Test reporting mirror successes."""
        manager = MirrorManager(config_dir=temp_config_dir)
        
        # Add test mirror
        test_url = "https://test.example.org/"
        manager.add_mirror(
            name="Test Mirror", 
            base_url=test_url, 
            priority=3
        )
        
        # Set initial failure state
        mirror_index = next(i for i, m in enumerate(manager.mirrors) if m.base_url == test_url)
        manager.mirrors[mirror_index].health_score = 0.5
        manager.mirrors[mirror_index].active = False
        manager.failure_counts[test_url] = 5
        
        # Report a success
        manager.report_success(test_url)
        
        # Check effects
        assert manager.failure_counts[test_url] == 0  # Reset failure count
        assert manager.mirrors[mirror_index].health_score > 0.5  # Increased health
        assert manager.mirrors[mirror_index].active is True  # Reactivated

    def test_record_book_availability(self, temp_config_dir):
        """Test recording book availability on mirrors."""
        manager = MirrorManager(config_dir=temp_config_dir)
        
        # Record availability for a book
        book_id = 1234
        mirror_url = "https://test.example.org/"
        
        # Book should not be in availability map initially
        assert book_id not in manager.book_availability
        
        # Record availability
        manager.record_book_availability(book_id, mirror_url)
        
        # Check book is now tracked
        assert book_id in manager.book_availability
        assert mirror_url in manager.book_availability[book_id]
        
        # Add another mirror for the same book
        second_mirror = "https://second.example.org/"
        manager.record_book_availability(book_id, second_mirror)
        
        # Check both mirrors are tracked
        assert len(manager.book_availability[book_id]) == 2
        assert mirror_url in manager.book_availability[book_id]
        assert second_mirror in manager.book_availability[book_id]

    @patch('gutenberg_downloader.mirror_manager.httpx.Client')
    def test_check_mirror_health(self, mock_client, temp_config_dir, mirror_site, mock_response):
        """Test checking mirror health."""
        # Mock response for successful check
        mock_client.return_value.head.return_value = mock_response
        
        manager = MirrorManager(config_dir=temp_config_dir)
        
        # Set an initial health score below maximum
        mirror_site.health_score = 0.5
        mirror_site.last_checked = None
        mirror_site.last_success = None
        
        # Check health
        result = manager.check_mirror_health(mirror_site)
        
        # Check result and mirror updates
        assert result is True
        assert mirror_site.health_score > 0.5  # Health increased
        assert mirror_site.last_checked is not None
        assert mirror_site.last_success is not None
        assert mirror_site.active is True
        
        # Test failure handling
        mock_response.status_code = 500
        
        # Reset mirror state
        mirror_site.health_score = 0.8
        mirror_site.active = True
        
        # Check health with error response
        result = manager.check_mirror_health(mirror_site)
        
        # Check failure results
        assert result is False
        assert mirror_site.health_score < 0.8  # Health decreased
        assert mirror_site.active is True  # Still active after one failure
        
        # Test connection error
        mock_client.return_value.head.side_effect = httpx.HTTPError("Connection error")
        
        # Reset mirror state
        mirror_site.health_score = 0.8
        mirror_site.active = True
        
        # Check health with connection error
        result = manager.check_mirror_health(mirror_site)
        
        # Check connection error results
        assert result is False
        assert mirror_site.health_score < 0.8  # Health decreased significantly
        assert mirror_site.active is True  # Still active after one failure

    def test_check_all_mirrors(self, temp_config_dir):
        """Test checking all mirrors."""
        with patch.object(MirrorManager, 'check_mirror_health') as mock_check:
            # Set up mocked behavior - alternate between success and failure
            mock_check.side_effect = [True, False, True]
            
            manager = MirrorManager(config_dir=temp_config_dir)
            
            # Keep only 3 test mirrors for simplicity
            manager.mirrors = [
                MirrorSite(name="Mirror 1", base_url="https://mirror1.example.org/"),
                MirrorSite(name="Mirror 2", base_url="https://mirror2.example.org/"),
                MirrorSite(name="Mirror 3", base_url="https://mirror3.example.org/")
            ]
            
            # Check all mirrors
            results = manager.check_all_mirrors()
            
            # Check results
            assert len(results) == 3
            assert results["https://mirror1.example.org/"] is True
            assert results["https://mirror2.example.org/"] is False
            assert results["https://mirror3.example.org/"] is True
            
            # Check that each mirror was checked
            assert mock_check.call_count == 3

    def test_get_book_url(self, temp_config_dir):
        """Test getting book URL from selected mirror."""
        with patch.object(MirrorManager, 'select_mirror') as mock_select:
            mock_select.return_value = "https://selected.example.org/"
            
            with patch.object(MirrorManager, 'build_book_url') as mock_build:
                mock_build.return_value = "https://selected.example.org/ebooks/1234.epub"
                
                manager = MirrorManager(config_dir=temp_config_dir)
                book_id = 1234
                
                # Get book URL
                url = manager.get_book_url(book_id)
                
                # Check correct methods were called
                mock_select.assert_called_once_with(book_id)
                mock_build.assert_called_once_with(book_id, "https://selected.example.org/")
                
                # Check returned URL
                assert url == "https://selected.example.org/ebooks/1234.epub"