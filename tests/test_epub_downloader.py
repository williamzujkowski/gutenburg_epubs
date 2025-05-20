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
            
    def test_resume_download_with_existing_file(self, downloader, tmp_path):
        """Test that download can resume from an existing file."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "resumable_book.epub"
        
        # Create partial content already in file
        existing_content = b"Partial EPUB content"
        output_path.write_bytes(existing_content)
        
        # Additional content to be downloaded
        additional_content = b" - Rest of the content"
        full_content = existing_content + additional_content
        
        # Mock HEAD request for file size
        head_response = Mock()
        head_response.headers = {"content-length": str(len(full_content))}
        head_response.raise_for_status = Mock()
        downloader.client.head.return_value = head_response
        
        # Mock first request with Range header
        range_response = Mock()
        range_response.status_code = 206  # Partial Content
        range_response.headers = {"content-length": str(len(additional_content))}
        range_response.raise_for_status = Mock()
        range_response.iter_bytes = Mock(return_value=[additional_content])
        range_response.__enter__ = Mock(return_value=range_response)
        range_response.__exit__ = Mock(return_value=None)
        
        # Create a mock that checks if the Range header is set correctly
        def stream_side_effect(method, url, headers=None, **kwargs):
            if headers and "Range" in headers:
                if headers["Range"] == f"bytes={len(existing_content)}-":
                    return range_response
            return None
        
        downloader.client.stream = Mock(side_effect=stream_side_effect)
        
        # Use a mocked open to avoid actual file operations
        # but verify the mode is "ab" for appending
        mock_open = Mock()
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch("builtins.open", mock_open):
            result = downloader.download_epub(url, output_path, resume=True)
            
            # Check that Range header was used
            downloader.client.stream.assert_called_once()
            mock_open.assert_called_once()
            
            # Verify append mode was used
            args, kwargs = mock_open.call_args
            assert args[1] == "ab"  # Should be in append mode
            
            assert result is True
    
    def test_server_does_not_support_resume(self, downloader, tmp_path):
        """Test behavior when server doesn't support resume."""
        url = "https://example.com/book.epub"
        output_path = tmp_path / "non_resumable_book.epub"
        
        # Create partial content already in file
        existing_content = b"Partial EPUB content"
        output_path.write_bytes(existing_content)
        
        # Content for full download
        full_content = b"Complete different content"
        
        # Mock HEAD request
        head_response = Mock()
        head_response.headers = {"content-length": str(len(full_content))}
        head_response.raise_for_status = Mock()
        downloader.client.head.return_value = head_response
        
        # Mock range request that doesn't return 206
        non_range_response = Mock()
        non_range_response.status_code = 200  # OK but not Partial Content
        non_range_response.headers = {"content-length": str(len(full_content))}
        non_range_response.raise_for_status = Mock()
        non_range_response.iter_bytes = Mock(return_value=[full_content])
        non_range_response.__enter__ = Mock(return_value=non_range_response)
        non_range_response.__exit__ = Mock(return_value=None)
        
        # Standard response for second request
        standard_response = Mock()
        standard_response.status_code = 200
        standard_response.headers = {"content-length": str(len(full_content))}
        standard_response.raise_for_status = Mock()
        standard_response.iter_bytes = Mock(return_value=[full_content])
        standard_response.__enter__ = Mock(return_value=standard_response)
        standard_response.__exit__ = Mock(return_value=None)
        
        # Side effect to handle the two requests
        request_count = 0
        def stream_side_effect(method, url, headers=None, **kwargs):
            nonlocal request_count
            
            if request_count == 0:
                request_count += 1
                return non_range_response
            else:
                return standard_response
        
        downloader.client.stream = Mock(side_effect=stream_side_effect)
        
        # Use a mocked open to verify mode changes
        mock_open = Mock()
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch("builtins.open", mock_open):
            result = downloader.download_epub(url, output_path, resume=True)
            
            # Check stream was called twice - once with Range, once without
            assert downloader.client.stream.call_count == 2
            assert result is True
            
            # Verify calls to open
            assert mock_open.call_count == 1
            
            # The second call should be in write mode, not append mode
            args, kwargs = mock_open.call_args
            assert args[1] == "wb"  # Should fall back to write mode
    
    def test_find_incomplete_downloads(self, downloader, tmp_path):
        """Test finding incomplete downloads in a directory."""
        # Create complete and incomplete files
        incomplete1 = tmp_path / "incomplete1.epub"
        incomplete2 = tmp_path / "incomplete2.epub"
        complete = tmp_path / "complete.epub"
        non_epub = tmp_path / "not_an_epub.txt"
        
        # Write some content (incomplete files under 10KB)
        incomplete1.write_bytes(b"Small content 1")
        incomplete2.write_bytes(b"Small content 2")
        
        # Write a complete file (> 10KB)
        complete.write_bytes(b"X" * 11000)  # 11KB, should be considered complete
        
        # Create a non-EPUB file
        non_epub.write_bytes(b"Not an EPUB file")
        
        # Find incomplete downloads
        result = downloader.find_incomplete_downloads(tmp_path)
        
        # Should find only the incomplete EPUB files
        assert len(result) == 2
        file_paths = [p.name for p in result]
        assert "incomplete1.epub" in file_paths
        assert "incomplete2.epub" in file_paths
        assert "complete.epub" not in file_paths
        assert "not_an_epub.txt" not in file_paths
    
    def test_resume_incomplete_downloads(self, downloader, tmp_path):
        """Test resuming multiple incomplete downloads."""
        # Create incomplete files
        file1 = tmp_path / "book1.epub"
        file2 = tmp_path / "book2.epub"
        file1.write_bytes(b"Partial content 1")
        file2.write_bytes(b"Partial content 2")
        
        # Define URL mapping
        url_mapping = {
            file1: "https://example.com/book1.epub",
            file2: "https://example.com/book2.epub",
            tmp_path / "non_existent.epub": "https://example.com/non_existent.epub"
        }
        
        # Mock download_epub to succeed for file1 and fail for file2
        def download_side_effect(url, output_path, **kwargs):
            if str(output_path) == str(file1):
                return True
            else:
                return False
                
        with patch.object(
            downloader, "download_epub", side_effect=download_side_effect
        ):
            results = downloader.resume_incomplete_downloads(
                [file1, file2, tmp_path / "non_existent.epub"],  # Include a non-existent file
                url_mapping
            )
            
            # Should have results for all three files
            assert len(results) == 3
            assert results[file1] is True
            assert results[file2] is False
            assert results[tmp_path / "non_existent.epub"] is False  # Should fail
            
            # download_epub should be called twice (once for each existing file)
            assert downloader.download_epub.call_count == 2
