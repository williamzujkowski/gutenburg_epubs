"""Tests for the Gutendex API client."""

import json
from pathlib import Path
import pytest
from unittest.mock import patch, Mock, MagicMock

import httpx

from gutenberg_downloader.api_client import GutendexAPIClient


@pytest.fixture
def mock_response():
    """Create a mock response fixture."""
    mock = Mock()
    mock.json.return_value = {
        "count": 1,
        "next": None,
        "previous": None,
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
                ],
                "languages": ["en"],
                "download_count": 46283,
                "formats": {
                    "application/epub+zip": "https://www.gutenberg.org/ebooks/1342.epub.images"
                },
                "subjects": ["England -- Fiction", "Love stories"]
            }
        ]
    }
    mock.status_code = 200
    return mock


class TestGutendexAPIClient:
    """Tests for the GutendexAPIClient class."""

    def test_init(self):
        """Test client initialization."""
        client = GutendexAPIClient(timeout=30, use_cache=False)
        assert client.timeout == 30
        assert client.use_cache is False
        assert client.cache is None
        assert isinstance(client.session, httpx.Client)

    def test_context_manager(self):
        """Test client as context manager."""
        with patch('gutenberg_downloader.api_client.httpx.Client') as mock_client:
            with GutendexAPIClient() as client:
                pass
            mock_client.return_value.close.assert_called_once()

    def test_make_request(self, mock_response):
        """Test making a request."""
        with patch('gutenberg_downloader.api_client.httpx.Client') as mock_client:
            mock_client.return_value.get.return_value = mock_response
            client = GutendexAPIClient(use_cache=False)
            result = client._make_request('/books')
            
            assert result == mock_response.json.return_value
            mock_client.return_value.get.assert_called_once_with(
                f"{GutendexAPIClient.BASE_URL}/books", 
                params=None
            )

    def test_make_request_with_params(self, mock_response):
        """Test making a request with parameters."""
        with patch('gutenberg_downloader.api_client.httpx.Client') as mock_client:
            mock_client.return_value.get.return_value = mock_response
            client = GutendexAPIClient(use_cache=False)
            params = {'search': 'pride', 'languages': 'en'}
            result = client._make_request('/books', params=params)
            
            assert result == mock_response.json.return_value
            mock_client.return_value.get.assert_called_once_with(
                f"{GutendexAPIClient.BASE_URL}/books", 
                params=params
            )

    def test_cached_request(self, mock_response, tmp_path):
        """Test cached request."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        with patch('gutenberg_downloader.api_client.httpx.Client') as mock_client:
            mock_client.return_value.get.return_value = mock_response
            client = GutendexAPIClient(use_cache=True, cache_dir=str(cache_dir))
            
            # First request should hit the API
            result1 = client._make_request('/books', params={'search': 'pride'})
            assert result1 == mock_response.json.return_value
            mock_client.return_value.get.assert_called_once()
            
            # Reset mock
            mock_client.reset_mock()
            
            # Second request with same params should use cache
            result2 = client._make_request('/books', params={'search': 'pride'})
            assert result2 == mock_response.json.return_value
            mock_client.return_value.get.assert_not_called()

    def test_get_books(self, mock_response):
        """Test get_books method."""
        with patch.object(GutendexAPIClient, '_make_request') as mock_request:
            mock_request.return_value = mock_response.json.return_value
            client = GutendexAPIClient(use_cache=False)
            
            result = client.get_books(search='pride', languages='en')
            
            mock_request.assert_called_once_with(
                '/books', 
                params={'search': 'pride', 'languages': 'en'}
            )
            assert result == mock_response.json.return_value

    def test_get_book_by_id(self, mock_response):
        """Test get_book_by_id method."""
        book_id = 1342
        with patch.object(GutendexAPIClient, '_make_request') as mock_request:
            mock_request.return_value = mock_response.json.return_value
            client = GutendexAPIClient(use_cache=False)
            
            result = client.get_book_by_id(book_id)
            
            mock_request.assert_called_once_with(f'/books/{book_id}')
            assert result == mock_response.json.return_value

    def test_search_books(self, mock_response):
        """Test search_books method."""
        with patch.object(GutendexAPIClient, '_make_request') as mock_request:
            mock_request.return_value = mock_response.json.return_value
            client = GutendexAPIClient(use_cache=False)
            
            result = client.search_books('pride and prejudice')
            
            mock_request.assert_called_once_with(
                '/books', 
                params={'search': 'pride and prejudice'}
            )
            assert result == mock_response.json.return_value

    def test_error_handling(self):
        """Test error handling."""
        with patch('gutenberg_downloader.api_client.httpx.Client') as mock_client:
            mock_client.return_value.get.side_effect = httpx.HTTPError("Connection error")
            
            client = GutendexAPIClient(use_cache=False)
            
            with pytest.raises(httpx.HTTPError):
                client._make_request('/books')