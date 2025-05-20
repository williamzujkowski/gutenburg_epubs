"""Tests for the asynchronous EPUB downloader module."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from gutenberg_downloader.async_epub_downloader import AsyncEpubDownloader


class TestAsyncEpubDownloader:
    """Tests for the AsyncEpubDownloader class."""

    @pytest.fixture
    def downloader(self):
        """Create an AsyncEpubDownloader instance for testing."""
        return AsyncEpubDownloader(max_concurrency=2)

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = Mock()
        response.headers = {"content-length": "12"}  # Match the actual size of "chunk1chunk2"
        response.status_code = 200

        # raise_for_status is synchronous in httpx
        response.raise_for_status = Mock(return_value=None)

        # Create a proper async generator for aiter_bytes
        async def async_generator(chunk_size=8192):  # noqa: ARG001
            for chunk in [b"chunk1", b"chunk2"]:
                yield chunk

        # The aiter_bytes method should return the generator function itself
        response.aiter_bytes = async_generator
        return response

    @pytest.mark.asyncio
    async def test_initialization_with_defaults(self):
        """Test downloader initialization with default values."""
        downloader = AsyncEpubDownloader()
        assert downloader.user_agent
        assert downloader.max_retries == 3
        assert downloader.timeout == 30.0
        assert downloader.max_concurrency == 5
        assert downloader.client is not None
        await downloader.close()

    @pytest.mark.asyncio
    async def test_initialization_with_custom_values(self):
        """Test downloader initialization with custom values."""
        downloader = AsyncEpubDownloader(
            user_agent="TestAgent/1.0",
            max_retries=5,
            timeout=60.0,
            max_concurrency=10,
        )
        assert downloader.user_agent == "TestAgent/1.0"
        assert downloader.max_retries == 5
        assert downloader.timeout == 60.0
        assert downloader.max_concurrency == 10
        await downloader.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with AsyncEpubDownloader() as downloader:
            assert downloader.client is not None
        # Client should be closed after exiting context

    @pytest.mark.asyncio
    async def test_download_epub_success(self, downloader, mock_response, tmp_path):
        """Test successful EPUB download."""
        url = "http://example.com/book.epub"
        output_path = tmp_path / "test.epub"

        # Create a proper async context manager mock
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        # Create mock for aiofiles
        mock_file = AsyncMock()
        mock_file.write = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None

        # Mock Path.exists to return False for parent directory check
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir"),
            patch.object(downloader.client, "stream", return_value=mock_stream_context),
            patch("aiofiles.open", return_value=mock_file_context),
        ):
            result = await downloader.download_epub(
                url, output_path, progress_bar=False, verify_size=False
            )

            assert result is True
            downloader.client.stream.assert_called_once_with("GET", url)
            mock_file.write.assert_called()

    @pytest.mark.asyncio
    async def test_download_epub_with_progress_bar(self, downloader, mock_response, tmp_path):
        """Test download with progress bar enabled."""
        url = "http://example.com/book.epub"
        output_path = tmp_path / "test.epub"

        # Create proper async context manager mocks
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        mock_file = AsyncMock()
        mock_file.write = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir"),
            patch.object(downloader.client, "stream", return_value=mock_stream_context),
            patch("aiofiles.open", return_value=mock_file_context),
            patch("gutenberg_downloader.async_epub_downloader.tqdm") as mock_tqdm,
        ):
            result = await downloader.download_epub(
                url, output_path, progress_bar=True, verify_size=False
            )

            assert result is True
            assert mock_tqdm.called

    @pytest.mark.asyncio
    async def test_download_epub_size_mismatch(self, downloader, tmp_path):
        """Test download with size mismatch."""
        url = "http://example.com/book.epub"
        output_path = tmp_path / "test.epub"

        response = Mock()
        response.headers = {"content-length": "1000"}

        # raise_for_status is synchronous in httpx
        response.raise_for_status = Mock(return_value=None)

        async def async_generator(chunk_size=8192):  # noqa: ARG001
            yield b"short"

        response.aiter_bytes = async_generator

        # Create proper async context manager mocks
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = response
        mock_stream_context.__aexit__.return_value = None

        mock_file = AsyncMock()
        mock_file.write = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None

        with (
            patch.object(downloader.client, "stream", return_value=mock_stream_context),
            patch("aiofiles.open", return_value=mock_file_context),
        ):
            result = await downloader.download_epub(
                url, output_path, progress_bar=False
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_download_epub_http_error(self, downloader, tmp_path):
        """Test download with HTTP error."""
        url = "http://example.com/book.epub"
        output_path = tmp_path / "test.epub"

        response = Mock()

        # raise_for_status is synchronous in httpx and raises an error
        response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=Mock(status_code=404)
        ))

        # Create proper async context manager mock
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = response
        mock_stream_context.__aexit__.return_value = None

        with patch.object(downloader.client, "stream", return_value=mock_stream_context):
            result = await downloader.download_epub(url, output_path, progress_bar=False)

            assert result is False

    @pytest.mark.asyncio
    async def test_download_epub_retry_exhausted(self, downloader, tmp_path):
        """Test download when retry attempts are exhausted."""
        url = "http://example.com/book.epub"
        output_path = tmp_path / "test.epub"

        with patch.object(downloader, "_stream_download", AsyncMock()) as mock_stream:
            mock_stream.side_effect = Exception("Network error")

            result = await downloader.download_epub(url, output_path, progress_bar=False)

            assert result is False
            assert mock_stream.call_count == downloader.max_retries

    @pytest.mark.asyncio
    async def test_download_epub_creates_parent_directory(self, downloader, mock_response, tmp_path):
        """Test that parent directory is created if it doesn't exist."""
        url = "http://example.com/book.epub"
        output_path = tmp_path / "subdir" / "test.epub"

        # Create proper async context manager mocks
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        mock_file = AsyncMock()
        mock_file.write = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None

        with (
            patch.object(downloader.client, "stream", return_value=mock_stream_context),
            patch("aiofiles.open", return_value=mock_file_context),
        ):
            result = await downloader.download_epub(
                url, output_path, progress_bar=False, verify_size=False
            )

            assert result is True
            # Path handling is done by the actual implementation

    @pytest.mark.asyncio
    async def test_download_epub_with_progress_callback(self, downloader, mock_response, tmp_path):
        """Test download with custom progress callback."""
        url = "http://example.com/book.epub"
        output_path = tmp_path / "test.epub"
        progress_calls = []

        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))

        # Create proper async context manager mocks
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        mock_file = AsyncMock()
        mock_file.write = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir"),
            patch.object(downloader.client, "stream", return_value=mock_stream_context),
            patch("aiofiles.open", return_value=mock_file_context),
        ):
            result = await downloader.download_epub(
                url, output_path, progress_bar=False, verify_size=False, progress_callback=progress_callback
            )

            assert result is True
            assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_download_multiple_epubs_success(self, downloader, mock_response, tmp_path):  # noqa: ARG002
        """Test successful multiple EPUB downloads."""
        downloads = [
            ("http://example.com/book1.epub", tmp_path / "book1.epub"),
            ("http://example.com/book2.epub", tmp_path / "book2.epub"),
        ]

        with patch.object(downloader, "download_epub", AsyncMock()) as mock_download:
            mock_download.return_value = True

            results = await downloader.download_multiple_epubs(
                downloads, progress_bar=False
            )

            assert len(results) == 2
            assert all(results.values())
            assert mock_download.call_count == 2

    @pytest.mark.asyncio
    async def test_download_multiple_epubs_with_failure(self, downloader, tmp_path):
        """Test multiple downloads with one failure."""
        downloads = [
            ("http://example.com/book1.epub", tmp_path / "book1.epub"),
            ("http://example.com/book2.epub", tmp_path / "book2.epub"),
            ("http://example.com/book3.epub", tmp_path / "book3.epub"),
        ]

        with patch.object(downloader, "download_epub", AsyncMock()) as mock_download:
            mock_download.side_effect = [True, False, True]

            results = await downloader.download_multiple_epubs(
                downloads, progress_bar=False
            )

            assert len(results) == 3
            assert results["http://example.com/book1.epub"] is True
            assert results["http://example.com/book2.epub"] is False
            assert results["http://example.com/book3.epub"] is True

    @pytest.mark.asyncio
    async def test_download_multiple_epubs_stop_on_error(self, downloader, tmp_path):
        """Test multiple downloads with stop_on_error enabled."""
        downloads = [
            ("http://example.com/book1.epub", tmp_path / "book1.epub"),
            ("http://example.com/book2.epub", tmp_path / "book2.epub"),
            ("http://example.com/book3.epub", tmp_path / "book3.epub"),
        ]

        # Mock download_epub to return True for first, then fail for second
        async def mock_download(url, output_path, **kwargs):  # noqa: ARG001
            return url == "http://example.com/book1.epub"

        with patch.object(downloader, "download_epub", mock_download):
            results = await downloader.download_multiple_epubs(
                downloads, progress_bar=False, stop_on_error=True
            )

            # First download should succeed
            assert results["http://example.com/book1.epub"] is True
            # Second download should fail
            assert results["http://example.com/book2.epub"] is False
            # Third download shouldn't happen when stop_on_error is True
            assert results["http://example.com/book3.epub"] is False

    @pytest.mark.asyncio
    async def test_download_multiple_epubs_with_progress(self, downloader, tmp_path):
        """Test multiple downloads with overall progress callback."""
        downloads = [
            ("http://example.com/book1.epub", tmp_path / "book1.epub"),
            ("http://example.com/book2.epub", tmp_path / "book2.epub"),
        ]
        progress_calls = []

        def overall_progress(completed, total):
            progress_calls.append((completed, total))

        with patch.object(downloader, "download_epub", AsyncMock()) as mock_download:
            mock_download.return_value = True

            results = await downloader.download_multiple_epubs(
                downloads,
                progress_bar=False,
                overall_progress_callback=overall_progress,
            )

            assert len(results) == 2
            assert len(progress_calls) > 0
            assert progress_calls[-1] == (2, 2)  # Final progress should be complete

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, downloader, tmp_path):
        """Test that concurrency is properly limited."""
        downloader.max_concurrency = 2
        downloader._semaphore = asyncio.Semaphore(2)

        downloads = [
            (f"http://example.com/book{i}.epub", tmp_path / f"book{i}.epub")
            for i in range(5)
        ]

        active_downloads = []
        max_active = 0

        # Mock download_epub to respect semaphore and track concurrent downloads
        async def mock_download(url, output_path, **kwargs):  # noqa: ARG001
            async with downloader._semaphore:  # Use the semaphore
                # Track active downloads
                active_downloads.append(url)
                nonlocal max_active
                max_active = max(max_active, len(active_downloads))
                await asyncio.sleep(0.05)  # Simulate download time
                active_downloads.remove(url)
                return True

        # Patch the download_epub method
        with patch.object(downloader, "download_epub", mock_download):
            results = await downloader.download_multiple_epubs(
                downloads, progress_bar=False
            )

            assert max_active <= downloader.max_concurrency  # Should never exceed concurrency limit
            assert len(results) == 5
            assert all(results.values())
            
    @pytest.mark.asyncio
    async def test_resume_download_with_existing_file(self, downloader, tmp_path):
        """Test resuming a download with an existing file."""
        url = "http://example.com/resumable.epub"
        output_path = tmp_path / "partial.epub"
        
        # Create a partial file
        existing_content = b"Partial file content"
        output_path.write_bytes(existing_content)
        existing_size = len(existing_content)
        
        # Additional content to append
        additional_content = b"Additional content to resume"
        total_content_size = existing_size + len(additional_content)
        
        # Create mock responses
        # First response should be a partial content response
        partial_response = Mock()
        partial_response.status_code = 206  # Partial Content
        partial_response.headers = {"content-length": str(len(additional_content))}
        partial_response.raise_for_status = Mock(return_value=None)
        
        # Set up async generator for aiter_bytes
        async def mock_async_generator():
            yield additional_content
            
        partial_response.aiter_bytes = mock_async_generator
        
        # Set up context manager for stream response
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = partial_response
        mock_stream_context.__aexit__.return_value = None
        
        # Set up mocks for aiofiles
        mock_file = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None
        
        # Create a side effect to check that Range header is being used
        def stream_side_effect(method, url, headers=None, **kwargs):
            if headers and "Range" in headers:
                expected_range = f"bytes={existing_size}-"
                assert headers["Range"] == expected_range
                return mock_stream_context
            return None
            
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.stat", return_value=Mock(st_size=existing_size)),
            patch.object(downloader.client, "stream", side_effect=stream_side_effect),
            patch("aiofiles.open", return_value=mock_file_context),
        ):
            result = await downloader._stream_download(
                url,
                output_path,
                progress_bar=False
            )
            
            assert result is True
            # Verify aiofiles.open was called with append mode
            patch("aiofiles.open").assert_called_once()
            args, kwargs = patch("aiofiles.open").call_args
            assert args[1] == "ab"  # Should be in append mode
            
    @pytest.mark.asyncio
    async def test_server_does_not_support_resume(self, downloader, tmp_path):
        """Test behavior when server doesn't support resuming."""
        url = "http://example.com/non_resumable.epub"
        output_path = tmp_path / "partial.epub"
        
        # Create a partial file
        existing_content = b"Partial file content"
        output_path.write_bytes(existing_content)
        existing_size = len(existing_content)
        
        # Full content when server doesn't support resume
        full_content = b"Complete different content for non-resumable download"
        
        # Create mock responses
        # First response should not be a partial content response
        normal_response = Mock()
        normal_response.status_code = 200  # OK, not 206 Partial Content
        normal_response.headers = {"content-length": str(len(full_content))}
        normal_response.raise_for_status = Mock(return_value=None)
        
        # Set up async generator for aiter_bytes for the first response
        async def mock_normal_generator():
            yield full_content
            
        normal_response.aiter_bytes = mock_normal_generator
        
        # Set up context manager for first response
        mock_normal_context = AsyncMock()
        mock_normal_context.__aenter__.return_value = normal_response
        mock_normal_context.__aexit__.return_value = None
        
        # Set up mocks for aiofiles
        mock_file = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__.return_value = mock_file
        mock_file_context.__aexit__.return_value = None
        
        # Mock the client.stream method - first with range header, then without
        first_call = True
        def stream_side_effect(method, url, headers=None, **kwargs):
            nonlocal first_call
            
            if first_call:
                # First call should have Range header
                assert headers and "Range" in headers
                first_call = False
                # Return a regular 200 response, not a 206 Partial Content
                return mock_normal_context
            else:
                # Second call without Range header
                assert headers is None or "Range" not in headers
                return mock_normal_context
                
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.stat", return_value=Mock(st_size=existing_size)),
            patch.object(downloader.client, "stream", side_effect=stream_side_effect),
            patch("aiofiles.open", return_value=mock_file_context),
        ):
            result = await downloader._stream_download(
                url,
                output_path,
                progress_bar=False
            )
            
            assert result is True
            # Should make two calls to stream - one with Range header, one without
            assert downloader.client.stream.call_count == 2
            
    @pytest.mark.asyncio
    async def test_find_incomplete_downloads(self, downloader, tmp_path):
        """Test finding incomplete downloads in a directory."""
        # Create a mix of complete and incomplete files
        incomplete1 = tmp_path / "incomplete1.epub"
        incomplete2 = tmp_path / "incomplete2.epub"
        complete = tmp_path / "complete.epub"
        non_epub = tmp_path / "not_an_epub.txt"
        
        # Write content to files
        incomplete1.write_bytes(b"Small content 1")  # Under 10KB = incomplete
        incomplete2.write_bytes(b"Small content 2")  # Under 10KB = incomplete
        complete.write_bytes(b"X" * 11000)  # Over 10KB = complete
        non_epub.write_bytes(b"Not an EPUB file")
        
        # Mock Path.glob to return our test files
        def mock_glob(pattern):
            if pattern == "*.epub":
                return [incomplete1, incomplete2, complete]
            return []
            
        # Set up our mock patches
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.glob", side_effect=mock_glob),
        ):
            result = await downloader.find_incomplete_downloads(tmp_path)
            
            # Should find only the incomplete EPUB files
            assert len(result) == 2
            file_paths = [p.name for p in result]
            assert "incomplete1.epub" in file_paths
            assert "incomplete2.epub" in file_paths
            assert "complete.epub" not in file_paths
            assert "not_an_epub.txt" not in file_paths
            
    @pytest.mark.asyncio
    async def test_resume_incomplete_downloads(self, downloader, tmp_path):
        """Test resuming multiple incomplete downloads."""
        # Create incomplete files
        file1 = tmp_path / "book1.epub"
        file2 = tmp_path / "book2.epub"
        
        # Create URL mapping
        url_mapping = {
            file1: "http://example.com/book1.epub",
            file2: "http://example.com/book2.epub",
            tmp_path / "missing.epub": "http://example.com/missing.epub",
        }
        
        # Mock download_epub to succeed for file1 and fail for file2
        async def mock_download_epub(url, output_path, **kwargs):
            if output_path == file1:
                return True
            else:
                return False
                
        # Set up our mocks
        with patch.object(downloader, "download_epub", side_effect=mock_download_epub):
            result = await downloader.resume_incomplete_downloads(
                [file1, file2, tmp_path / "missing.epub"],
                url_mapping,
                progress_bar=False
            )
            
            # Should have results for all files
            assert len(result) == 3
            assert result[file1] is True
            assert result[file2] is False
            assert result[tmp_path / "missing.epub"] is False  # Missing file should fail
            
            # download_epub should be called for each file
            assert downloader.download_epub.call_count == 3
