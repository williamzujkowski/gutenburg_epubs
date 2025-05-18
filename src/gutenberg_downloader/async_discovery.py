"""Asynchronous book discovery module for Project Gutenberg.

This module provides async functionality for discovering and downloading English books
with EPUB files from Project Gutenberg using concurrent operations.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional, Union

from .async_epub_downloader import AsyncEpubDownloader
from .discovery import BookDiscovery
from .scraper import GutenbergScraper

logger = logging.getLogger(__name__)


class AsyncBookDiscovery(BookDiscovery):
    """Async-enabled book discovery for Project Gutenberg."""

    def __init__(
        self,
        scraper: Optional[GutenbergScraper] = None,
        downloader: Optional[AsyncEpubDownloader] = None,
        max_concurrency: int = 5,
    ):
        """Initialize the async book discovery system.

        Args:
            scraper: Optional GutenbergScraper instance.
            downloader: Optional AsyncEpubDownloader instance.
            max_concurrency: Maximum concurrent operations.
        """
        # Initialize base class with synchronous components
        super().__init__(scraper=scraper, downloader=None)

        # Set up async downloader
        self.async_downloader = downloader or AsyncEpubDownloader(
            max_concurrency=max_concurrency
        )
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def __aenter__(self) -> "AsyncBookDiscovery":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager and clean up resources."""
        await self.close_async()

    async def close_async(self) -> None:
        """Close async resources."""
        await self.async_downloader.close()
        # Also close synchronous resources
        self.close()

    async def discover_popular_english_epubs_async(
        self, limit: int = 100, min_downloads: Optional[int] = None  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Asynchronously discover popular English books with EPUB files.

        This method fetches book details concurrently for better performance.

        Args:
            limit: Maximum number of books to return.
            min_downloads: Minimum download count filter (if available).

        Returns:
            List of dictionaries containing book information including EPUB URLs.
        """
        # Get popular books synchronously (this is fast)
        popular_books = self.scraper.get_popular_books(limit=limit * 2)

        # Fetch book details concurrently
        english_books_with_epub: list[dict[str, Any]] = []
        tasks = []

        for book in popular_books:
            if len(english_books_with_epub) >= limit:
                break

            task = self._get_book_details_if_english_epub(book["book_id"])
            tasks.append(task)

        # Execute tasks concurrently
        results = list(await asyncio.gather(*tasks, return_exceptions=True))

        # Process results
        for book, result in zip(popular_books, results):
            if isinstance(result, Exception):
                logger.error(f"Error getting details for book {book['book_id']}: {result}")
                continue

            if result is not None and not isinstance(result, BaseException):  # Book is English with EPUB
                result["popularity_rank"] = len(english_books_with_epub) + 1
                result["title"] = book.get("title", result.get("metadata", {}).get("title"))
                english_books_with_epub.append(result)

                if len(english_books_with_epub) >= limit:
                    break

        return english_books_with_epub

    async def _get_book_details_if_english_epub(
        self, book_id: int
    ) -> Optional[dict[str, Any]]:
        """Get book details if it's an English book with EPUB.

        Args:
            book_id: Project Gutenberg book ID.

        Returns:
            Book details if it's English with EPUB, None otherwise.
        """
        async with self._semaphore:
            # Use synchronous method wrapped in executor
            book_details = await asyncio.get_event_loop().run_in_executor(
                None, self.get_book_details, book_id
            )

            if book_details and self._is_english_with_epub(book_details):
                return book_details

            return None

    async def download_book_epub_async(
        self,
        book_id: int,
        output_path: Union[str, Path],
        book_details: Optional[dict[str, Any]] = None,
        progress_bar: bool = True,
    ) -> bool:
        """Asynchronously download the EPUB file for a specific book.

        Args:
            book_id: Project Gutenberg book ID.
            output_path: Path where the EPUB should be saved.
            book_details: Optional pre-fetched book details.
            progress_bar: Whether to show progress bar.

        Returns:
            True if download was successful, False otherwise.
        """
        if not book_details:
            # Get book details asynchronously
            book_details = await asyncio.get_event_loop().run_in_executor(
                None, self.get_book_details, book_id
            )

        if not book_details:
            logger.error(f"Could not get details for book {book_id}")
            return False

        epub_url = book_details.get("download_links", {}).get("epub")

        if not epub_url:
            logger.error(f"No EPUB URL found for book {book_id}")
            return False

        return await self.async_downloader.download_epub(
            epub_url, output_path, progress_bar=progress_bar
        )

    async def download_multiple_books_async(
        self,
        book_ids: list[int],
        output_dir: Union[str, Path],
        progress_bar: bool = True,
        skip_existing: bool = True,
        stop_on_error: bool = False,
    ) -> dict[int, bool]:
        """Download multiple books concurrently.

        Args:
            book_ids: List of book IDs to download.
            output_dir: Directory to save downloaded files.
            progress_bar: Whether to show progress bars.
            skip_existing: Whether to skip already downloaded files.
            stop_on_error: Whether to stop all downloads on first error.

        Returns:
            Dictionary mapping book IDs to download success status.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # First, fetch all book details concurrently
        logger.info(f"Fetching details for {len(book_ids)} books...")

        detail_tasks = []
        for book_id in book_ids:
            task = asyncio.get_event_loop().run_in_executor(
                None, self.get_book_details, book_id
            )
            detail_tasks.append(task)

        book_details_list = await asyncio.gather(*detail_tasks, return_exceptions=True)

        # Prepare download list
        downloads: list[tuple[str, Union[str, Path]]] = []
        results = {}

        for book_id, details in zip(book_ids, book_details_list):
            if isinstance(details, Exception):
                logger.error(f"Error getting details for book {book_id}: {details}")
                results[book_id] = False
                continue

            if not details:
                logger.error(f"No details found for book {book_id}")
                results[book_id] = False
                continue

            if isinstance(details, dict):
                epub_url = details.get("download_links", {}).get("epub")
            else:
                logger.error(f"Invalid details type for book {book_id}: {type(details)}")
                results[book_id] = False
                continue
            if not epub_url:
                logger.error(f"No EPUB URL for book {book_id}")
                results[book_id] = False
                continue

            # Generate filename from title (we know details is a dict from above)
            title = details.get("metadata", {}).get("title", f"book_{book_id}")
            clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            clean_title = clean_title.replace(" ", "_")
            filename = f"{clean_title}.epub"
            output_path = output_dir / filename

            # Skip if exists
            if skip_existing and output_path.exists():
                logger.info(f"Skipping {book_id}: {title} (already exists)")
                results[book_id] = True
                continue

            downloads.append((epub_url, output_path))

        # Download EPUBs concurrently
        if downloads:
            logger.info(f"Downloading {len(downloads)} EPUB files...")

            download_results = await self.async_downloader.download_multiple_epubs(
                downloads,
                progress_bar=progress_bar,
                stop_on_error=stop_on_error,
            )

            # Map results back to book IDs
            for (epub_url, _), book_id in zip(downloads, book_ids):
                if book_id not in results:  # Not already set (skipped/error)
                    results[book_id] = download_results.get(epub_url, False)

        # Summary
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Successfully processed {successful}/{len(book_ids)} books")

        return results

    async def search_and_download_async(
        self,
        search_term: str,
        search_type: str = "title",
        output_dir: Union[str, Path] = "downloads",
        limit: int = 10,
        exact_match: bool = False,
        download_all: bool = False,
    ) -> dict[str, Any]:
        """Search for books and optionally download them.

        Args:
            search_term: Term to search for.
            search_type: Type of search ("title" or "author").
            output_dir: Directory for downloads.
            limit: Maximum number of results.
            exact_match: Whether to require exact match (title search only).
            download_all: Whether to download all found books.

        Returns:
            Dictionary with search results and download status.
        """
        # Perform search using synchronous methods
        if search_type == "title":
            results = self.search_by_title(search_term, exact_match=exact_match, limit=limit)
        elif search_type == "author":
            results = self.search_by_author(search_term, limit=limit)
        else:
            raise ValueError(f"Invalid search type: {search_type}")

        response = {
            "search_term": search_term,
            "search_type": search_type,
            "results_found": len(results),
            "results": results,
            "downloads": {},
        }

        if download_all and results:
            # Extract book IDs from results
            book_ids = [book["book_id"] for book in results]

            # Download all books concurrently
            download_results = await self.download_multiple_books_async(
                book_ids,
                output_dir,
                progress_bar=True,
                skip_existing=True,
            )

            response["downloads"] = download_results

        return response
