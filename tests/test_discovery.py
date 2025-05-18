"""Tests for the book discovery module."""

from unittest.mock import Mock, patch

import pytest

from gutenberg_downloader.constants import BASE_URL
from gutenberg_downloader.discovery import BookDiscovery


class TestBookDiscovery:
    """Tests for the BookDiscovery class."""

    @pytest.fixture
    def mock_scraper(self):
        """Create a mock scraper."""
        return Mock()

    @pytest.fixture
    def mock_downloader(self):
        """Create a mock downloader."""
        return Mock()

    @pytest.fixture
    def discovery(self, mock_scraper, mock_downloader):
        """Create a discovery instance with mocked dependencies."""
        return BookDiscovery(scraper=mock_scraper, downloader=mock_downloader)

    @pytest.fixture
    def sample_book_details(self):
        """Sample book details for testing."""
        return {
            "book_id": 123,
            "metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "language": "English",
            },
            "download_links": {
                "epub": f"{BASE_URL}/ebooks/123.epub",
                "txt": f"{BASE_URL}/ebooks/123.txt",
            },
        }

    def test_initialization_with_defaults(self):
        """Test discovery initializes with default dependencies."""
        with (
            patch("gutenberg_downloader.discovery.GutenbergScraper") as MockScraper,
            patch("gutenberg_downloader.discovery.EpubDownloader") as MockDownloader,
        ):
            discovery = BookDiscovery()

            MockScraper.assert_called_once()
            MockDownloader.assert_called_once()
            assert discovery.scraper is not None
            assert discovery.downloader is not None

    def test_initialization_with_custom_dependencies(
        self, mock_scraper, mock_downloader
    ):
        """Test discovery initializes with provided dependencies."""
        discovery = BookDiscovery(scraper=mock_scraper, downloader=mock_downloader)

        assert discovery.scraper is mock_scraper
        assert discovery.downloader is mock_downloader

    def test_context_manager(self, discovery):
        """Test discovery works as a context manager."""
        discovery.close = Mock()

        with discovery as d:
            assert d is discovery

        discovery.close.assert_called_once()

    def test_close(self, discovery):
        """Test closing cleans up resources."""
        discovery.close()

        discovery.scraper.close.assert_called_once()
        discovery.downloader.close.assert_called_once()

    def test_discover_popular_english_epubs(self, discovery, sample_book_details):
        """Test discovering popular English books with EPUB files."""
        import copy

        # Mock popular books
        popular_books = [
            {"book_id": 123, "title": "Book 1"},
            {"book_id": 456, "title": "Book 2"},
            {"book_id": 789, "title": "Book 3"},
        ]
        discovery.scraper.get_popular_books.return_value = popular_books

        # Mock book details - first is English with EPUB, second is not English, third is English without EPUB
        book_details_1 = copy.deepcopy(sample_book_details)
        book_details_2 = {
            "book_id": 456,
            "metadata": {"language": "French"},
            "download_links": {"epub": "url"},
        }
        book_details_3 = {
            "book_id": 789,
            "metadata": {"language": "English"},
            "download_links": {"txt": "url"},
        }

        # Use patch.object to properly mock the method
        with patch.object(
            discovery,
            "get_book_details",
            side_effect=[book_details_1, book_details_2, book_details_3],
        ):
            # Discover books
            results = discovery.discover_popular_english_epubs(limit=2)

            assert len(results) == 1
            assert results[0]["book_id"] == 123
            assert results[0]["popularity_rank"] == 1

            # Should have called get_popular_books with extra limit
            discovery.scraper.get_popular_books.assert_called_once_with(limit=4)

    def test_get_book_details_success(self, discovery, sample_book_details):
        """Test getting book details successfully."""
        book_id = 123
        html_content = "<html>Book page</html>"

        discovery.scraper.fetch_page.return_value = html_content
        discovery.scraper.parse_book_page.return_value = sample_book_details

        result = discovery.get_book_details(book_id)

        assert result == sample_book_details
        discovery.scraper.fetch_page.assert_called_once_with(
            f"{BASE_URL}/ebooks/{book_id}"
        )
        discovery.scraper.parse_book_page.assert_called_once_with(html_content)

    def test_get_book_details_fetch_failure(self, discovery):
        """Test getting book details when fetch fails."""
        book_id = 123

        discovery.scraper.fetch_page.return_value = None

        result = discovery.get_book_details(book_id)

        assert result is None
        discovery.scraper.fetch_page.assert_called_once()
        discovery.scraper.parse_book_page.assert_not_called()

    def test_get_book_details_exception(self, discovery):
        """Test getting book details when exception occurs."""
        book_id = 123

        discovery.scraper.fetch_page.side_effect = Exception("Network error")

        result = discovery.get_book_details(book_id)

        assert result is None

    def test_search_by_title_exact_match(self, discovery, sample_book_details):
        """Test searching by exact title match."""
        popular_books = [
            {"book_id": 123, "title": "Test Book"},
            {"book_id": 456, "title": "Another Book"},
        ]
        discovery.scraper.get_popular_books.return_value = popular_books

        with patch.object(
            discovery, "get_book_details", return_value=sample_book_details
        ) as mock_get_details:
            results = discovery.search_by_title("Test Book", exact_match=True)

            assert len(results) == 1
            assert results[0]["book_id"] == 123

            # Should only have fetched details for exact match
            mock_get_details.assert_called_once_with(123)

    def test_search_by_title_partial_match(self, discovery, sample_book_details):
        """Test searching by partial title match."""
        popular_books = [
            {"book_id": 123, "title": "Test Book One"},
            {"book_id": 456, "title": "Test Book Two"},
            {"book_id": 789, "title": "Different Book"},
        ]
        discovery.scraper.get_popular_books.return_value = popular_books

        with patch.object(
            discovery, "get_book_details", return_value=sample_book_details
        ) as mock_get_details:
            results = discovery.search_by_title("Test Book", exact_match=False, limit=2)

            assert len(results) == 2
            # Should have fetched details for partial matches
            assert mock_get_details.call_count == 2

    def test_search_by_author(self, discovery, sample_book_details):
        """Test searching by author."""
        import copy

        popular_books = [
            {"book_id": 123, "title": "Book 1"},
            {"book_id": 456, "title": "Book 2"},
        ]
        discovery.scraper.get_popular_books.return_value = popular_books

        # Mock different authors
        book_1 = copy.deepcopy(sample_book_details)
        book_1["metadata"]["author"] = "Test Author"

        book_2 = copy.deepcopy(sample_book_details)
        book_2["book_id"] = 456
        book_2["metadata"]["author"] = "Different Author"

        with patch.object(discovery, "get_book_details", side_effect=[book_1, book_2]):
            results = discovery.search_by_author("Test")

            assert len(results) == 1
            assert results[0]["book_id"] == 123

    def test_filter_by_language(self, discovery):
        """Test filtering books by language."""
        books = [
            {"metadata": {"language": "English"}},
            {"metadata": {"language": "French"}},
            {"metadata": {"language": "en"}},
            {"metadata": {"language": "Spanish"}},
        ]

        results = discovery.filter_by_language(books, "en")

        # Note: filter_by_language looks for language code in the string,
        # so "English" matches "en" and "en" matches "en"
        assert len(results) == 2

    def test_filter_by_format(self, discovery):
        """Test filtering books by format."""
        books = [
            {"download_links": {"epub": "url1", "txt": "url2"}},
            {"download_links": {"txt": "url3"}},
            {"download_links": {"epub": "url4", "pdf": "url5"}},
            {"download_links": {"pdf": "url6"}},
        ]

        results = discovery.filter_by_format(books, "epub")

        assert len(results) == 2
        assert "epub" in results[0]["download_links"]
        assert "epub" in results[1]["download_links"]

    def test_is_english_with_epub(self, discovery, sample_book_details):
        """Test checking if book is English with EPUB."""
        import copy

        # English with EPUB
        assert discovery._is_english_with_epub(sample_book_details) is True

        # French with EPUB
        french_book = copy.deepcopy(sample_book_details)
        french_book["metadata"]["language"] = "French"
        assert discovery._is_english_with_epub(french_book) is False

        # English without EPUB
        no_epub_book = copy.deepcopy(sample_book_details)
        no_epub_book["download_links"] = {"txt": "url"}
        assert discovery._is_english_with_epub(no_epub_book) is False

    def test_get_catalog_stats(self, discovery, sample_book_details):
        """Test getting catalog statistics."""
        import copy

        popular_books = [
            {"book_id": 1},
            {"book_id": 2},
            {"book_id": 3},
        ]
        discovery.scraper.get_popular_books.return_value = popular_books

        # Mock different book types
        english_epub = copy.deepcopy(sample_book_details)
        french_epub = copy.deepcopy(sample_book_details)
        french_epub["metadata"]["language"] = "French"
        english_txt = copy.deepcopy(sample_book_details)
        english_txt["download_links"] = {"txt": "url"}

        with patch.object(
            discovery,
            "get_book_details",
            side_effect=[english_epub, french_epub, english_txt],
        ):
            stats = discovery.get_catalog_stats()

            assert stats["total_books_sampled"] == 3
            assert stats["english_books"] == 2
            assert stats["books_with_epub"] == 2
            assert stats["english_books_with_epub"] == 1

    def test_download_book_epub_success(self, discovery, sample_book_details):
        """Test downloading book EPUB successfully."""
        book_id = 123
        output_path = "test.epub"

        discovery.downloader.download_epub.return_value = True

        with patch.object(
            discovery, "get_book_details", return_value=sample_book_details
        ):
            result = discovery.download_book_epub(book_id, output_path)

            assert result is True
            discovery.downloader.download_epub.assert_called_once_with(
                sample_book_details["download_links"]["epub"], output_path
            )

    def test_download_book_epub_with_provided_details(
        self, discovery, sample_book_details
    ):
        """Test downloading book EPUB with pre-fetched details."""
        book_id = 123
        output_path = "test.epub"

        discovery.downloader.download_epub.return_value = True

        with patch.object(discovery, "get_book_details") as mock_get_details:
            result = discovery.download_book_epub(
                book_id, output_path, book_details=sample_book_details
            )

            assert result is True
            mock_get_details.assert_not_called()
            discovery.downloader.download_epub.assert_called_once()

    def test_download_book_epub_no_details(self, discovery):
        """Test downloading book EPUB when details not found."""
        book_id = 123
        output_path = "test.epub"

        with patch.object(discovery, "get_book_details", return_value=None):
            result = discovery.download_book_epub(book_id, output_path)

            assert result is False
            discovery.downloader.download_epub.assert_not_called()

    def test_download_book_epub_no_epub_url(self, discovery, sample_book_details):
        """Test downloading book EPUB when no EPUB URL available."""
        book_id = 123
        output_path = "test.epub"

        # Remove EPUB from download links
        no_epub_book = sample_book_details.copy()
        no_epub_book["download_links"] = {"txt": "url"}

        with patch.object(discovery, "get_book_details", return_value=no_epub_book):
            result = discovery.download_book_epub(book_id, output_path)

            assert result is False
            discovery.downloader.download_epub.assert_not_called()
