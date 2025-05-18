"""Tests for the EPUB downloader module."""

import io
from unittest.mock import Mock, patch

import httpx
import pytest

from gutenberg_downloader.constants import DEFAULT_USER_AGENT
from gutenberg_downloader.epub_downloader import EpubDownloader


class TestEpubDownloader:
    """Tests for the EpubDownloader class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return Mock(spec=httpx.Client)

    @pytest.fixture
    def downloader(self, mock_client):
        """Create a downloader instance with mocked HTTP client."""
        with patch(
            "gutenberg_downloader.epub_downloader.httpx.Client",
            return_value=mock_client,
        ):
            downloader = EpubDownloader()
            downloader.client = mock_client
            return downloader

    def test_initialization_with_defaults(self):
        """Test downloader initializes with default values."""
        downloader = EpubDownloader()

        assert downloader.user_agent == DEFAULT_USER_AGENT
        assert downloader.timeout == 30.0
        assert downloader.chunk_size == 8192

    def test_initialization_with_custom_values(self):
        """Test downloader initializes with custom values."""
        custom_agent = "CustomAgent/1.0"
        custom_timeout = 60.0
        custom_chunk_size = 16384

        downloader = EpubDownloader(
            user_agent=custom_agent,
            timeout=custom_timeout,
            chunk_size=custom_chunk_size,
        )

        assert downloader.user_agent == custom_agent
        assert downloader.timeout == custom_timeout
        assert downloader.chunk_size == custom_chunk_size

    def test_context_manager(self, downloader):
        """Test downloader works as a context manager."""
        downloader.close = Mock()

        with downloader as d:
            assert d is downloader

        downloader.close.assert_called_once()

    def test_download_epub_success(self, downloader, tmp_path):
        """Test successful EPUB download."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "book.epub"
        content = b"Mock EPUB content"

        # Mock HEAD request for file size
        head_response = Mock()
        head_response.headers = {"content-length": str(len(content))}
        head_response.raise_for_status = Mock()
        downloader.client.head.return_value = head_response

        # Mock streaming response
        mock_response = Mock()
        mock_response.headers = {"content-length": str(len(content))}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes = Mock(return_value=[content])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)

        # Download the file
        with patch("gutenberg_downloader.epub_downloader.tqdm") as mock_tqdm:
            result = downloader.download_epub(url, output_path)

        assert result is True
        assert output_path.exists()
        assert output_path.read_bytes() == content

        # Verify tqdm was used for progress
        mock_tqdm.assert_called_once()

    def test_download_epub_no_progress_bar(self, downloader, tmp_path):
        """Test EPUB download without progress bar."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "book.epub"
        content = b"Mock EPUB content"

        # Mock streaming response
        mock_response = Mock()
        mock_response.headers = {"content-length": str(len(content))}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes = Mock(return_value=[content])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)
        head_response = Mock()
        head_response.headers = {"content-length": str(len(content))}
        head_response.raise_for_status = Mock()
        downloader.client.head = Mock(return_value=head_response)

        # Download the file without progress bar
        with patch("gutenberg_downloader.epub_downloader.tqdm") as mock_tqdm:
            result = downloader.download_epub(url, output_path, progress_bar=False)

        assert result is True
        assert output_path.exists()
        mock_tqdm.assert_not_called()

    def test_download_epub_size_mismatch(self, downloader, tmp_path):
        """Test download failure when size doesn't match."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "book.epub"
        content = b"Mock EPUB content"

        # Mock HEAD request with different size
        head_response = Mock()
        head_response.headers = {"content-length": "1000"}  # Wrong size
        head_response.raise_for_status = Mock()
        downloader.client.head.return_value = head_response

        # Mock streaming response
        mock_response = Mock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes = Mock(return_value=[content])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)

        # Download should fail due to size mismatch
        result = downloader.download_epub(url, output_path)

        assert result is False
        assert not output_path.exists()  # File should be cleaned up

    def test_download_epub_http_error(self, downloader, tmp_path):
        """Test download failure with HTTP error."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "book.epub"

        # Mock HTTP error on GET request
        error = httpx.HTTPError("404 Not Found")
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = error
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        downloader.client.stream = Mock(return_value=mock_response)

        # Mock successful HEAD request
        head_response = Mock()
        head_response.headers = {"content-length": "100"}
        head_response.raise_for_status = Mock()
        downloader.client.head = Mock(return_value=head_response)

        with pytest.raises(httpx.HTTPError):
            downloader.download_epub(url, output_path)

        assert not output_path.exists()

    def test_download_epub_io_error(self, downloader, tmp_path):
        """Test download failure with IO error."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "book.epub"

        # Mock successful HEAD request
        head_response = Mock()
        head_response.headers = {"content-length": "100"}
        head_response.raise_for_status = Mock()
        downloader.client.head.return_value = head_response

        # Mock streaming response
        mock_response = Mock()
        mock_response.headers = {"content-length": "100"}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes = Mock(return_value=[b"content"])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)

        # Mock IO error during file write
        with (
            patch("builtins.open", side_effect=OSError("Disk full")),
            pytest.raises(OSError),
        ):
            downloader.download_epub(url, output_path)

        assert not output_path.exists()

    def test_download_epub_creates_parent_directory(self, downloader, tmp_path):
        """Test that download creates parent directories if needed."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "nested" / "dir" / "book.epub"
        content = b"Mock EPUB content"

        # Mock streaming response
        mock_response = Mock()
        mock_response.headers = {"content-length": str(len(content))}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes = Mock(return_value=[content])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)
        head_response = Mock()
        head_response.headers = {"content-length": str(len(content))}
        head_response.raise_for_status = Mock()
        downloader.client.head = Mock(return_value=head_response)

        # Download should create parent directories
        result = downloader.download_epub(url, output_path, verify_size=False)

        assert result is True
        assert output_path.exists()
        assert output_path.parent.exists()
        assert output_path.read_bytes() == content

    def test_download_multiple_epubs_success(self, downloader, tmp_path):
        """Test downloading multiple EPUBs successfully."""
        downloads = [
            ("https://example.com/book1.epub", tmp_path / "book1.epub"),
            ("https://example.com/book2.epub", tmp_path / "book2.epub"),
            ("https://example.com/book3.epub", tmp_path / "book3.epub"),
        ]

        # Mock successful downloads
        with (
            patch.object(
                downloader, "download_epub", return_value=True
            ) as mock_download,
            patch("time.sleep") as mock_sleep,
        ):
            results = downloader.download_multiple_epubs(downloads, delay=0.5)

        assert all(results.values())
        assert len(results) == 3

        # Verify delays were applied
        assert mock_sleep.call_count == 2  # No delay before first download
        mock_sleep.assert_called_with(0.5)

        # Verify all downloads were attempted
        assert mock_download.call_count == 3

    def test_download_multiple_epubs_with_failure(self, downloader, tmp_path):
        """Test downloading multiple EPUBs with one failure."""
        downloads = [
            ("https://example.com/book1.epub", tmp_path / "book1.epub"),
            ("https://example.com/book2.epub", tmp_path / "book2.epub"),
            ("https://example.com/book3.epub", tmp_path / "book3.epub"),
        ]

        # Mock downloads: first succeeds, second fails, third succeeds
        download_results = [True, False, True]
        with patch.object(downloader, "download_epub", side_effect=download_results):
            results = downloader.download_multiple_epubs(downloads)

        assert results[downloads[0][0]] is True
        assert results[downloads[1][0]] is False
        assert results[downloads[2][0]] is True

    def test_download_multiple_epubs_stop_on_error(self, downloader, tmp_path):
        """Test downloading multiple EPUBs stopping on first error."""
        downloads = [
            ("https://example.com/book1.epub", tmp_path / "book1.epub"),
            ("https://example.com/book2.epub", tmp_path / "book2.epub"),
            ("https://example.com/book3.epub", tmp_path / "book3.epub"),
        ]

        # Mock downloads: first succeeds, second fails
        download_results = [True, False]
        with patch.object(downloader, "download_epub", side_effect=download_results):
            results = downloader.download_multiple_epubs(
                downloads, continue_on_error=False
            )

        # Should only have results for first two
        assert len(results) == 2
        assert results[downloads[0][0]] is True
        assert results[downloads[1][0]] is False

    def test_stream_download_success(self, downloader):
        """Test successful stream download."""
        url = "https://example.com/book.epub"
        content = b"Mock EPUB content"
        output_stream = io.BytesIO()

        # Mock streaming response
        mock_response = Mock()
        mock_response.headers = {"content-length": str(len(content))}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes = Mock(return_value=[content])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)

        # Test without progress callback
        bytes_downloaded = downloader.stream_download(url, output_stream)

        assert bytes_downloaded == len(content)
        assert output_stream.getvalue() == content

    def test_stream_download_with_progress_callback(self, downloader):
        """Test stream download with progress callback."""
        url = "https://example.com/book.epub"
        content = b"Mock EPUB content"
        output_stream = io.BytesIO()
        progress_calls = []

        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))

        # Mock streaming response
        mock_response = Mock()
        mock_response.headers = {"content-length": str(len(content))}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes = Mock(return_value=[content])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)

        # Download with progress callback
        bytes_downloaded = downloader.stream_download(
            url, output_stream, progress_callback=progress_callback
        )

        assert bytes_downloaded == len(content)
        assert output_stream.getvalue() == content
        assert len(progress_calls) == 1
        assert progress_calls[0] == (len(content), len(content))

    def test_stream_download_http_error(self, downloader):
        """Test stream download with HTTP error."""
        url = "https://example.com/book.epub"
        output_stream = io.BytesIO()

        # Mock HTTP error
        error = httpx.HTTPError("404 Not Found")
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = error
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)

        downloader.client.stream = Mock(return_value=mock_response)

        with pytest.raises(httpx.HTTPError):
            downloader.stream_download(url, output_stream)
