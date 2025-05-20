"""Async book discovery service using the Gutendex API."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from .async_api_client import AsyncGutendexAPIClient
from .async_epub_downloader import AsyncEpubDownloader

logger = logging.getLogger(__name__)


class AsyncAPIBookDiscovery:
    """Async service for discovering books via the Gutendex API."""
    
    def __init__(self, max_concurrency: int = 5):
        """Initialize the discovery service.
        
        Args:
            max_concurrency: Maximum concurrent operations
        """
        self.api_client = AsyncGutendexAPIClient()
        self.downloader = AsyncEpubDownloader(max_concurrency=max_concurrency)
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        logger.info("Initialized async API-based book discovery")
    
    async def __aenter__(self):
        """Enter async context manager."""
        await self.api_client.__aenter__()
        await self.downloader.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
        await self.downloader.__aexit__(exc_type, exc_val, exc_tb)
    
    def _format_book_data(self, api_book: dict[str, Any]) -> dict[str, Any]:
        """Format API book data to match our internal structure.
        
        Args:
            api_book: Book data from API
            
        Returns:
            Formatted book data
        """
        # Extract author names
        authors = []
        for author in api_book.get("authors", []):
            if author.get("name"):
                authors.append(author["name"])
        
        # Find EPUB download URL
        epub_url = None
        formats = api_book.get("formats", {})
        for fmt, url in formats.items():
            if "epub" in fmt.lower() and url:
                epub_url = url
                break
        
        # Get language
        languages = api_book.get("languages", [])
        language = languages[0] if languages else "unknown"
        
        # Get subjects (for genre)
        subjects = api_book.get("subjects", [])
        
        return {
            "book_id": api_book.get("id"),
            "title": api_book.get("title", "Unknown Title"),
            "author": ", ".join(authors) if authors else "Unknown Author",
            "language": language,
            "formats": list(formats.keys()),
            "download_links": {
                "epub": epub_url,
                **formats  # Include all formats
            },
            "metadata": {
                "title": api_book.get("title"),
                "author": ", ".join(authors),
                "language": language,
                "subjects": subjects,
                "copyright": api_book.get("copyright"),
                "download_count": api_book.get("download_count", 0),
            },
            "popularity_rank": None,  # API doesn't provide explicit rank
        }
    
    async def discover_popular_english_epubs_async(
        self,
        limit: int = 100,
        min_downloads: Optional[int] = None,
        get_all: bool = False,
    ) -> list[dict[str, Any]]:
        """Discover popular English books with EPUB files asynchronously.
        
        Args:
            limit: Maximum number of books to return (ignored if get_all=True)
            min_downloads: Minimum download count (if supported by API)
            get_all: Whether to get all available books
            
        Returns:
            List of book dictionaries with metadata
        """
        try:
            if get_all:
                logger.info("Discovering all English EPUB books via API")
                api_books = await self.api_client.get_all_english_books_with_epub()
            else:
                logger.info(f"Discovering up to {limit} popular English EPUB books via API")
                api_books = await self.api_client.get_english_books_with_epub(limit=limit)
            
            formatted_books = []
            for api_book in api_books:
                # Format the book data
                book_data = self._format_book_data(api_book)
                
                # Apply min_downloads filter if specified
                if min_downloads and book_data["metadata"].get("download_count", 0) < min_downloads:
                    continue
                
                formatted_books.append(book_data)
            
            # Sort by download count (popularity)
            formatted_books.sort(
                key=lambda x: x["metadata"].get("download_count", 0),
                reverse=True
            )
            
            logger.info(f"Found {len(formatted_books)} English books with EPUB files")
            return formatted_books[:limit] if not get_all else formatted_books
            
        except Exception as e:
            logger.error(f"Error discovering books via API: {e}")
            return []
    
    async def search_by_title_async(
        self,
        title: str,
        exact_match: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search for books by title asynchronously.
        
        Args:
            title: Title to search for
            exact_match: Whether to require exact title match
            limit: Maximum number of results
            
        Returns:
            List of matching books
        """
        try:
            logger.info(f"Searching for books with title: {title}")
            
            api_books = await self.api_client.get_english_books_with_epub(
                limit=limit,
                search=title
            )
            
            formatted_books = []
            for api_book in api_books:
                book_data = self._format_book_data(api_book)
                
                # Apply exact match filter if requested
                if exact_match:
                    book_title = book_data.get("title", "").lower()
                    if title.lower() != book_title:
                        continue
                
                formatted_books.append(book_data)
            
            logger.info(f"Found {len(formatted_books)} books matching title: {title}")
            return formatted_books
            
        except Exception as e:
            logger.error(f"Error searching by title: {e}")
            return []
    
    async def get_book_by_id_async(self, book_id: int) -> Optional[dict[str, Any]]:
        """Get book details by Project Gutenberg ID asynchronously.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            Book details or None if not found
        """
        try:
            logger.info(f"Getting book details for ID: {book_id}")
            
            api_book = await self.api_client.get_book(book_id)
            book_data = self._format_book_data(api_book)
            
            return book_data
            
        except Exception as e:
            logger.error(f"Error getting book {book_id}: {e}")
            return None
    
    async def _download_single_book(
        self,
        book_id: int,
        output_dir: Path,
        book_details: Optional[dict[str, Any]] = None,
        progress_bar: bool = True,
        skip_existing: bool = True,
    ) -> bool:
        """Download a single book asynchronously.
        
        Args:
            book_id: Book ID to download
            output_dir: Output directory
            book_details: Optional pre-fetched book details
            progress_bar: Whether to show progress bar
            skip_existing: Whether to skip existing files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self._semaphore:
                # Get book details if not provided
                if not book_details:
                    book_details = await self.get_book_by_id_async(book_id)
                
                if not book_details:
                    logger.error(f"Book {book_id} not found")
                    return False
                
                # Generate filename
                title = book_details.get("title", f"book_{book_id}")
                clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                clean_title = clean_title.replace(" ", "_")
                filename = f"{clean_title}.epub"
                output_path = output_dir / filename
                
                # Skip if exists
                if skip_existing and output_path.exists():
                    logger.info(f"Skipping {book_id}: {title} (already exists)")
                    return True
                
                # Get EPUB URL
                epub_url = book_details.get("download_links", {}).get("epub")
                if not epub_url:
                    logger.error(f"No EPUB URL found for book {book_id}")
                    return False
                
                # Download the EPUB
                return await self.downloader.download_epub(
                    epub_url,
                    output_path,
                    progress_bar=progress_bar,
                )
                
        except Exception as e:
            logger.error(f"Error downloading book {book_id}: {e}")
            return False
    
    async def download_multiple_books_async(
        self,
        book_ids: list[int],
        output_dir: Path,
        progress_bar: bool = True,
        skip_existing: bool = True,
        stop_on_error: bool = False,
    ) -> dict[int, bool]:
        """Download multiple books concurrently.
        
        Args:
            book_ids: List of book IDs to download
            output_dir: Output directory
            progress_bar: Whether to show progress bars
            skip_existing: Whether to skip existing files
            stop_on_error: Whether to stop on first error
            
        Returns:
            Dictionary mapping book ID to download success
        """
        logger.info(f"Downloading {len(book_ids)} books via API...")
        
        # Create download tasks
        tasks = []
        for book_id in book_ids:
            task = self._download_single_book(
                book_id,
                output_dir,
                progress_bar=progress_bar,
                skip_existing=skip_existing,
            )
            tasks.append(task)
        
        # Execute downloads concurrently
        if stop_on_error:
            # Use gather with return_exceptions=False
            results = await asyncio.gather(*tasks, return_exceptions=False)
        else:
            # Use gather with return_exceptions=True
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build results dictionary
        download_results = {}
        for book_id, result in zip(book_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Error downloading book {book_id}: {result}")
                download_results[book_id] = False
            else:
                download_results[book_id] = result
        
        # Summary
        successful = sum(1 for success in download_results.values() if success)
        logger.info(f"Downloaded {successful}/{len(book_ids)} books successfully")
        
        return download_results