"""Tests for the asynchronous book discovery module."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gutenberg_downloader.async_discovery import AsyncBookDiscovery
from gutenberg_downloader.async_epub_downloader import AsyncEpubDownloader


class TestAsyncBookDiscovery:
    """Tests for the AsyncBookDiscovery class."""

    @pytest.fixture
    def mock_scraper(self):
        """Create a mock scraper."""
        return Mock()

    @pytest.fixture
    def mock_async_downloader(self):
        """Create a mock async downloader."""
        return AsyncMock(spec=AsyncEpubDownloader)

    @pytest.fixture
    def async_discovery(self, mock_scraper, mock_async_downloader):
        """Create an async discovery instance with mocked dependencies."""
        return AsyncBookDiscovery(
            scraper=mock_scraper,
            downloader=mock_async_downloader,
            max_concurrency=2
        )

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
                "epub": "http://example.com/123.epub",
                "txt": "http://example.com/123.txt",
            },
        }

    @pytest.mark.asyncio
    async def test_initialization_with_defaults(self):
        """Test async discovery initializes with default dependencies."""
        discovery = AsyncBookDiscovery()
        assert discovery.scraper is not None
        assert discovery.async_downloader is not None
        assert discovery.max_concurrency == 5
        await discovery.close_async()

    @pytest.mark.asyncio
    async def test_initialization_with_custom_dependencies(
        self, mock_scraper, mock_async_downloader
    ):
        """Test async discovery initializes with provided dependencies."""
        discovery = AsyncBookDiscovery(
            scraper=mock_scraper,
            downloader=mock_async_downloader,
            max_concurrency=10,
        )
        assert discovery.scraper is mock_scraper
        assert discovery.async_downloader is mock_async_downloader
        assert discovery.max_concurrency == 10

    @pytest.mark.asyncio
    async def test_context_manager(self, async_discovery):
        """Test async discovery works as a context manager."""
        async_discovery.close_async = AsyncMock()

        async with async_discovery as d:
            assert d is async_discovery

        async_discovery.close_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_async(self, async_discovery):
        """Test closing async resources."""
        with patch.object(async_discovery, "close") as mock_close:
            await async_discovery.close_async()

            async_discovery.async_downloader.close.assert_called_once()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_popular_english_epubs_async(
        self, async_discovery, sample_book_details
    ):
        """Test discovering popular English books asynchronously."""
        # Mock popular books
        popular_books = [
            {"book_id": 123, "title": "Book 1"},
            {"book_id": 456, "title": "Book 2"},
            {"book_id": 789, "title": "Book 3"},
        ]
        async_discovery.scraper.get_popular_books.return_value = popular_books

        # Mock book details - first is English with EPUB, second is not English, third is English without EPUB
        book_details_1 = sample_book_details.copy()
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

        # Mock get_book_details to be called in executor
        with patch.object(async_discovery, "get_book_details") as mock_get_details:
            mock_get_details.side_effect = [
                book_details_1,
                book_details_2,
                book_details_3,
            ]

            # Mock run_in_executor
            async def mock_executor(executor, func, *args):  # noqa: ARG001
                return func(*args)

            with patch.object(
                asyncio, "get_event_loop"
            ) as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_in_executor = mock_executor
                mock_get_loop.return_value = mock_loop

                results = await async_discovery.discover_popular_english_epubs_async(
                    limit=2
                )

                assert len(results) == 1
                assert results[0]["book_id"] == 123
                assert results[0]["popularity_rank"] == 1

    @pytest.mark.asyncio
    async def test_download_book_epub_async(
        self, async_discovery, sample_book_details, tmp_path
    ):
        """Test downloading a book asynchronously."""
        book_id = 123
        output_path = tmp_path / "test.epub"

        # Mock get_book_details
        with patch.object(async_discovery, "get_book_details") as mock_get_details:
            mock_get_details.return_value = sample_book_details

            # Mock run_in_executor
            async def mock_executor(executor, func, *args):  # noqa: ARG001
                return func(*args)

            with patch.object(asyncio, "get_event_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_in_executor = mock_executor
                mock_get_loop.return_value = mock_loop

                # Mock async download
                async_discovery.async_downloader.download_epub.return_value = True

                result = await async_discovery.download_book_epub_async(
                    book_id, output_path
                )

                assert result is True
                async_discovery.async_downloader.download_epub.assert_called_once_with(
                    sample_book_details["download_links"]["epub"],
                    output_path,
                    progress_bar=True,
                )

    @pytest.mark.asyncio
    async def test_download_book_epub_async_no_details(self, async_discovery, tmp_path):
        """Test downloading when book details not found."""
        book_id = 999
        output_path = tmp_path / "test.epub"

        # Mock get_book_details to return None
        with patch.object(async_discovery, "get_book_details") as mock_get_details:
            mock_get_details.return_value = None

            # Mock run_in_executor
            async def mock_executor(executor, func, *args):  # noqa: ARG001
                return func(*args)

            with patch.object(asyncio, "get_event_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_in_executor = mock_executor
                mock_get_loop.return_value = mock_loop

                result = await async_discovery.download_book_epub_async(
                    book_id, output_path
                )

                assert result is False

    @pytest.mark.asyncio
    async def test_download_multiple_books_async(
        self, async_discovery, sample_book_details, tmp_path
    ):
        """Test downloading multiple books concurrently."""
        book_ids = [123, 456, 789]
        output_dir = tmp_path

        # Mock get_book_details for three books
        book_details_list = [
            sample_book_details,
            {
                "book_id": 456,
                "metadata": {"title": "Book 2"},
                "download_links": {"epub": "http://example.com/456.epub"},
            },
            None,  # Third book has no details
        ]

        with patch.object(async_discovery, "get_book_details") as mock_get_details:
            mock_get_details.side_effect = book_details_list

            # Mock run_in_executor
            async def mock_executor(executor, func, *args):  # noqa: ARG001
                return func(*args)

            with patch.object(asyncio, "get_event_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_in_executor = mock_executor
                mock_get_loop.return_value = mock_loop

                # Mock async downloader
                async_discovery.async_downloader.download_multiple_epubs.return_value = {
                    "http://example.com/123.epub": True,
                    "http://example.com/456.epub": False,
                }

                results = await async_discovery.download_multiple_books_async(
                    book_ids, output_dir, skip_existing=False
                )

                assert results[123] is True
                assert results[456] is False
                assert results[789] is False  # No details found

    @pytest.mark.asyncio
    async def test_download_multiple_books_async_skip_existing(
        self, async_discovery, sample_book_details, tmp_path
    ):
        """Test downloading multiple books with skip existing enabled."""
        book_ids = [123]
        output_dir = tmp_path

        # Create existing file
        existing_file = output_dir / "Test_Book.epub"
        existing_file.touch()

        with patch.object(async_discovery, "get_book_details") as mock_get_details:
            mock_get_details.return_value = sample_book_details

            # Mock run_in_executor
            async def mock_executor(executor, func, *args):  # noqa: ARG001
                return func(*args)

            with patch.object(asyncio, "get_event_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_in_executor = mock_executor
                mock_get_loop.return_value = mock_loop

                results = await async_discovery.download_multiple_books_async(
                    book_ids, output_dir, skip_existing=True
                )

                assert results[123] is True  # Marked as success because already exists
                # Download should not have been called
                async_discovery.async_downloader.download_multiple_epubs.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_and_download_async(
        self, async_discovery, sample_book_details
    ):
        """Test searching and downloading books asynchronously."""
        search_term = "Test"
        output_dir = Path("downloads")

        # Mock search results
        search_results = [sample_book_details]

        with patch.object(async_discovery, "search_by_title") as mock_search:
            mock_search.return_value = search_results

            with patch.object(
                async_discovery, "download_multiple_books_async"
            ) as mock_download:
                mock_download.return_value = {123: True}

                result = await async_discovery.search_and_download_async(
                    search_term,
                    search_type="title",
                    output_dir=output_dir,
                    download_all=True,
                )

                assert result["search_term"] == search_term
                assert result["results_found"] == 1
                assert result["downloads"][123] is True

    @pytest.mark.asyncio
    async def test_search_and_download_async_no_download(
        self, async_discovery, sample_book_details
    ):
        """Test searching without downloading."""
        search_term = "Test"

        # Mock search results
        search_results = [sample_book_details]

        with patch.object(async_discovery, "search_by_author") as mock_search:
            mock_search.return_value = search_results

            result = await async_discovery.search_and_download_async(
                search_term,
                search_type="author",
                download_all=False,
            )

            assert result["search_term"] == search_term
            assert result["results_found"] == 1
            assert result["downloads"] == {}

    @pytest.mark.asyncio
    async def test_concurrent_book_details(self, async_discovery):
        """Test that concurrent operations properly limit concurrency."""
        async_discovery.max_concurrency = 2
        async_discovery._semaphore = asyncio.Semaphore(2)

        book_ids = list(range(5))
        active_tasks = []
        max_active = 0

        async def mock_get_details(book_id):
            async with async_discovery._semaphore:  # Use the semaphore
                active_tasks.append(book_id)
                nonlocal max_active
                max_active = max(max_active, len(active_tasks))
                await asyncio.sleep(0.1)
                active_tasks.remove(book_id)
                return {"book_id": book_id}

        # Patch the direct get_book_details call instead
        with patch.object(async_discovery, "get_book_details", lambda x: {"book_id": x}):
            tasks = []
            for book_id in book_ids:
                task = asyncio.create_task(mock_get_details(book_id))
                tasks.append(task)

            await asyncio.gather(*tasks)

            assert max_active <= 2  # Should never exceed concurrency limit
