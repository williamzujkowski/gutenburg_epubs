"""Tests for the Gutenberg scraper module."""

import time
from unittest.mock import Mock, patch

import httpx
import pytest

from gutenberg_downloader.constants import BASE_URL, DEFAULT_USER_AGENT
from gutenberg_downloader.scraper import GutenbergScraper


class TestGutenbergScraper:
    """Tests for the GutenbergScraper class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return Mock(spec=httpx.Client)

    @pytest.fixture
    def scraper(self, mock_client):
        """Create a scraper instance with mocked HTTP client."""
        with (
            patch(
                "gutenberg_downloader.scraper.httpx.Client", return_value=mock_client
            ),
            patch.object(GutenbergScraper, "_load_robots_txt"),
        ):
            scraper = GutenbergScraper()
            scraper.client = mock_client
            return scraper

    def test_initialization_with_defaults(self):
        """Test scraper initializes with default values."""
        with patch.object(GutenbergScraper, "_load_robots_txt"):
            scraper = GutenbergScraper()

            assert scraper.base_url == BASE_URL
            assert scraper.user_agent == DEFAULT_USER_AGENT
            assert scraper.delay == 1.0
            assert scraper.timeout == 30.0
            assert scraper.last_request_time is None

    def test_initialization_with_custom_values(self):
        """Test scraper initializes with custom values."""
        custom_url = "https://custom.url"
        custom_agent = "CustomAgent/1.0"
        custom_delay = 2.0
        custom_timeout = 60.0

        with patch.object(GutenbergScraper, "_load_robots_txt"):
            scraper = GutenbergScraper(
                base_url=custom_url,
                user_agent=custom_agent,
                delay=custom_delay,
                timeout=custom_timeout,
            )

            assert scraper.base_url == custom_url
            assert scraper.user_agent == custom_agent
            assert scraper.delay == custom_delay
            assert scraper.timeout == custom_timeout

    def test_context_manager(self, scraper):
        """Test scraper works as a context manager."""
        scraper.close = Mock()

        with scraper as s:
            assert s is scraper

        scraper.close.assert_called_once()

    def test_load_robots_txt_success(self):
        """Test successful loading of robots.txt."""
        mock_response = Mock()
        mock_response.text = "User-agent: *\nDisallow: /admin\n"
        mock_response.raise_for_status = Mock()

        with patch("gutenberg_downloader.scraper.httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch(
                "gutenberg_downloader.scraper.RobotExclusionRulesParser"
            ) as mock_parser_class:
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                GutenbergScraper()

                # Verify robots.txt was fetched
                mock_client.get.assert_called_with(
                    f"{BASE_URL}/robots.txt", timeout=10.0
                )
                mock_parser.parse.assert_called_with(
                    "User-agent: *\nDisallow: /admin\n"
                )

    def test_load_robots_txt_failure(self, mock_client):
        """Test handling of robots.txt loading failure."""
        mock_client.get.side_effect = httpx.HTTPError("Failed to fetch")

        # Should not raise exception
        scraper = GutenbergScraper()

        # Should have initialized empty parser
        assert scraper.robots_parser is not None

    def test_can_fetch_url_allowed(self, scraper):
        """Test URL fetch permission when allowed by robots.txt."""
        scraper.robots_parser = Mock()
        scraper.robots_parser.is_allowed.return_value = True

        result = scraper._can_fetch_url("https://example.com/page")

        assert result is True
        scraper.robots_parser.is_allowed.assert_called_with(
            scraper.user_agent, "https://example.com/page"
        )

    def test_can_fetch_url_disallowed(self, scraper):
        """Test URL fetch permission when disallowed by robots.txt."""
        scraper.robots_parser = Mock()
        scraper.robots_parser.is_allowed.return_value = False

        result = scraper._can_fetch_url("https://example.com/admin")

        assert result is False

    def test_can_fetch_url_no_parser(self, scraper):
        """Test URL fetch permission when no parser is available."""
        scraper.robots_parser = None

        result = scraper._can_fetch_url("https://example.com/page")

        assert result is True

    def test_enforce_delay_no_previous_request(self, scraper):
        """Test delay enforcement when no previous request exists."""
        scraper.last_request_time = None

        # Should not sleep
        with patch("time.sleep") as mock_sleep:
            scraper._enforce_delay()
            mock_sleep.assert_not_called()

    def test_enforce_delay_sufficient_time_passed(self, scraper):
        """Test delay enforcement when sufficient time has passed."""
        scraper.last_request_time = time.time() - 2.0  # 2 seconds ago
        scraper.delay = 1.0

        # Should not sleep
        with patch("time.sleep") as mock_sleep:
            scraper._enforce_delay()
            mock_sleep.assert_not_called()

    def test_enforce_delay_insufficient_time_passed(self, scraper):
        """Test delay enforcement when insufficient time has passed."""
        current_time = time.time()
        scraper.last_request_time = current_time - 0.5  # 0.5 seconds ago
        scraper.delay = 1.0

        with (
            patch("time.sleep") as mock_sleep,
            patch("time.time", return_value=current_time),
        ):
            scraper._enforce_delay()
            # Should sleep for approximately 0.5 seconds
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert 0.4 < sleep_time < 0.6

    def test_fetch_page_success(self, scraper):
        """Test successful page fetching."""
        url = "https://example.com/page"
        content = "<html><body>Content</body></html>"

        mock_response = Mock()
        mock_response.text = content
        mock_response.status_code = 200
        mock_response.content = content.encode()
        mock_response.raise_for_status = Mock()

        scraper.client.get.return_value = mock_response
        scraper._can_fetch_url = Mock(return_value=True)
        scraper._enforce_delay = Mock()

        result = scraper.fetch_page(url)

        assert result == content
        scraper._can_fetch_url.assert_called_with(url)
        scraper._enforce_delay.assert_called_once()
        scraper.client.get.assert_called_with(url)
        assert scraper.last_request_time is not None

    def test_fetch_page_relative_url(self, scraper):
        """Test fetching with relative URL."""
        relative_url = "/ebooks/123"
        absolute_url = f"{BASE_URL}/ebooks/123"

        mock_response = Mock()
        mock_response.text = "content"
        mock_response.status_code = 200
        mock_response.content = b"content"  # Add content as bytes
        mock_response.raise_for_status = Mock()

        scraper.client.get.return_value = mock_response
        scraper._can_fetch_url = Mock(return_value=True)
        scraper._enforce_delay = Mock()

        scraper.fetch_page(relative_url)

        scraper._can_fetch_url.assert_called_with(absolute_url)
        scraper.client.get.assert_called_with(absolute_url)

    def test_fetch_page_robots_disallowed(self, scraper):
        """Test fetching when disallowed by robots.txt."""
        url = "https://example.com/admin"

        scraper._can_fetch_url = Mock(return_value=False)

        result = scraper.fetch_page(url)

        assert result is None
        scraper.client.get.assert_not_called()

    def test_fetch_page_http_error(self, scraper):
        """Test fetching with HTTP error."""
        url = "https://example.com/notfound"

        error_response = Mock()
        error_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=error_response
        )

        scraper.client.get.side_effect = error
        scraper._can_fetch_url = Mock(return_value=True)
        scraper._enforce_delay = Mock()

        with pytest.raises(httpx.HTTPStatusError):
            scraper.fetch_page(url)

    def test_parse_book_page_complete(self):
        """Test parsing a complete book page."""
        html_content = """
        <html>
            <h1 itemprop="name">Test Book Title</h1>
            <a itemprop="creator">Test Author</a>
            <tr property="dcterms:language">
                <td>English</td>
            </tr>
            <a type="application/epub+zip" href="/ebooks/123.epub">EPUB</a>
            <meta property="og:url" content="https://www.gutenberg.org/ebooks/123" />
        </html>
        """

        scraper = GutenbergScraper()
        with patch.object(scraper, "_load_robots_txt"):
            result = scraper.parse_book_page(html_content)

        assert result["book_id"] == 123
        assert result["metadata"]["title"] == "Test Book Title"
        assert result["metadata"]["author"] == "Test Author"
        assert result["metadata"]["language"] == "English"
        assert result["download_links"]["epub"] == f"{BASE_URL}/ebooks/123.epub"

    def test_parse_book_page_missing_elements(self):
        """Test parsing a book page with missing elements."""
        html_content = """
        <html>
            <h1 itemprop="name">Test Book Title</h1>
        </html>
        """

        scraper = GutenbergScraper()
        with patch.object(scraper, "_load_robots_txt"):
            result = scraper.parse_book_page(html_content)

        assert result["metadata"]["title"] == "Test Book Title"
        assert "author" not in result["metadata"]
        assert "language" not in result["metadata"]
        assert result["download_links"] == {}
        assert result["book_id"] is None

    def test_parse_book_page_files_table(self):
        """Test parsing book page with files table."""
        html_content = """
        <html>
            <table class="files">
                <tr>
                    <td><a href="/files/123/123.txt">Plain Text</a></td>
                </tr>
                <tr>
                    <td><a href="/files/123/123.epub">EPUB</a></td>
                </tr>
            </table>
        </html>
        """

        scraper = GutenbergScraper()
        with patch.object(scraper, "_load_robots_txt"):
            result = scraper.parse_book_page(html_content)

        assert result["download_links"]["epub"] == f"{BASE_URL}/files/123/123.epub"

    def test_get_popular_books_success(self, scraper):
        """Test getting popular books list."""
        html_content = """
        <html>
            <ol class="pgdbbylanguage">
                <li><a href="/ebooks/123">Book 1</a></li>
                <li><a href="/ebooks/456">Book 2</a></li>
                <li><a href="/ebooks/789">Book 3</a></li>
            </ol>
        </html>
        """

        scraper.fetch_page = Mock(return_value=html_content)

        result = scraper.get_popular_books(limit=2)

        assert len(result) == 2
        assert result[0]["book_id"] == 123
        assert result[0]["title"] == "Book 1"
        assert result[0]["url"] == f"{BASE_URL}/ebooks/123"
        assert result[1]["book_id"] == 456
        assert result[1]["title"] == "Book 2"

    def test_get_popular_books_alternative_structure(self, scraper):
        """Test getting popular books with alternative HTML structure."""
        html_content = """
        <html>
            <ul>
                <li><a href="/ebooks/123">Book 1</a></li>
                <li><a href="/ebooks/456">Book 2</a></li>
            </ul>
        </html>
        """

        scraper.fetch_page = Mock(return_value=html_content)

        result = scraper.get_popular_books(limit=10)

        assert len(result) == 2
        assert result[0]["book_id"] == 123
        assert result[0]["title"] == "Book 1"

    def test_get_popular_books_no_content(self, scraper):
        """Test getting popular books when fetch fails."""
        scraper.fetch_page = Mock(return_value=None)

        result = scraper.get_popular_books()

        assert result == []

    def test_get_popular_books_no_list(self, scraper):
        """Test getting popular books with no book list."""
        html_content = "<html><body>No books here</body></html>"

        scraper.fetch_page = Mock(return_value=html_content)

        result = scraper.get_popular_books()

        assert result == []

    def test_get_popular_books_invalid_book_id(self, scraper):
        """Test handling invalid book IDs in popular books."""
        html_content = """
        <html>
            <ul>
                <li><a href="/ebooks/abc">Book 1</a></li>
                <li><a href="/ebooks/123">Book 2</a></li>
                <li><a href="/invalid/path">Book 3</a></li>
            </ul>
        </html>
        """

        scraper.fetch_page = Mock(return_value=html_content)

        result = scraper.get_popular_books()

        assert len(result) == 3
        assert "book_id" not in result[0]  # Invalid ID 'abc'
        assert result[1]["book_id"] == 123
        assert "book_id" not in result[2]  # Invalid path
