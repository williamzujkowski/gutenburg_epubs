"""Async client for accessing Project Gutenberg data via the Gutendex API."""

import asyncio
import logging
from typing import Any, Optional

import httpx

from .constants import (
    MAX_DOWNLOAD_RETRIES,
    MIN_DELAY_BETWEEN_REQUESTS,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


class AsyncGutendexAPIClient:
    """Async client for interacting with the Gutendex API."""

    BASE_URL = "https://gutendex.com"
    
    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        """Initialize the API client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session: Optional[httpx.AsyncClient] = None
        logger.info("Initialized Async Gutendex API client")
    
    async def __aenter__(self):
        """Enter async context manager."""
        self.session = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager and close session."""
        if self.session:
            await self.session.aclose()
    
    async def _make_request(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Make an async request to the API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            httpx.HTTPError: If request fails
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with statement.")
        
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(MAX_DOWNLOAD_RETRIES):
            try:
                response = await self.session.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{MAX_DOWNLOAD_RETRIES}): {e}")
                if attempt == MAX_DOWNLOAD_RETRIES - 1:
                    raise
                await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
    
    async def search_books(
        self,
        search: Optional[str] = None,
        languages: Optional[list[str]] = None,
        copyright: Optional[bool] = None,
        ids: Optional[list[int]] = None,
        topic: Optional[str] = None,
        author_year_start: Optional[int] = None,
        author_year_end: Optional[int] = None,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search for books using various filters.
        
        Args:
            search: Search text for title and author
            languages: List of language codes (e.g., ['en', 'fr'])
            copyright: Filter by copyright status
            ids: List of specific Gutenberg IDs
            topic: Search bookshelves and subjects
            author_year_start: Minimum author birth year
            author_year_end: Maximum author death year
            page: Page number for pagination
            
        Returns:
            API response with books and pagination info
        """
        params = {}
        
        if search:
            params["search"] = search
        if languages:
            params["languages"] = ",".join(languages)
        if copyright is not None:
            params["copyright"] = "true" if copyright else "false"
        if ids:
            params["ids"] = ",".join(map(str, ids))
        if topic:
            params["topic"] = topic
        if author_year_start:
            params["author_year_start"] = author_year_start
        if author_year_end:
            params["author_year_end"] = author_year_end
        if page > 1:
            params["page"] = page
        
        return await self._make_request("/books/", params)
    
    async def get_book(self, book_id: int) -> dict[str, Any]:
        """Get details for a specific book.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            Book details
        """
        return await self._make_request(f"/books/{book_id}")
    
    async def get_popular_books(
        self,
        languages: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get popular books sorted by download count.
        
        Args:
            languages: Filter by language codes
            limit: Maximum number of books to return
            
        Returns:
            List of popular books
        """
        results = []
        page = 1
        
        while len(results) < limit:
            response = await self.search_books(
                languages=languages,
                page=page,
            )
            
            books = response.get("results", [])
            if not books:
                break
            
            results.extend(books)
            
            # Check if there are more pages
            if not response.get("next"):
                break
            
            page += 1
        
        return results
    
    async def get_english_books_with_epub(
        self,
        limit: int = 100,
        search: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get English books that have EPUB format available.
        
        Args:
            limit: Maximum number of books to return
            search: Optional search term
            topic: Optional topic filter
            
        Returns:
            List of books with EPUB format up to the limit
        """
        results = []
        page = 1
        
        while len(results) < limit:
            response = await self.search_books(
                languages=["en"],
                search=search,
                topic=topic,
                page=page,
            )
            
            books = response.get("results", [])
            if not books:
                break
            
            # Filter for books with EPUB format
            for book in books:
                formats = book.get("formats", {})
                if any("epub" in fmt.lower() for fmt in formats.keys()):
                    results.append(book)
                    if len(results) >= limit:
                        break
            
            # Check if there are more pages
            if not response.get("next"):
                break
            
            page += 1
        
        return results
    
    async def get_all_english_books_with_epub(
        self,
        search: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get all English books that have EPUB format available without limit.
        
        Args:
            search: Optional search term
            topic: Optional topic filter
            
        Returns:
            List of all books with EPUB format
        """
        results = []
        page = 1
        
        while True:
            response = await self.search_books(
                languages=["en"],
                search=search,
                topic=topic,
                page=page,
            )
            
            books = response.get("results", [])
            if not books:
                break
            
            # Filter for books with EPUB format
            for book in books:
                formats = book.get("formats", {})
                if any("epub" in fmt.lower() for fmt in formats.keys()):
                    results.append(book)
            
            # Check if there are more pages
            if not response.get("next"):
                break
            
            page += 1
            logger.info(f"Fetched page {page}, total books: {len(results)}")
        
        return results