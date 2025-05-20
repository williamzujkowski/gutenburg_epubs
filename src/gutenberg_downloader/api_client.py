"""Client for accessing Project Gutenberg data via the Gutendex API."""

import logging
from typing import Any, Optional, Callable
from urllib.parse import urlencode

import httpx

from .constants import (
    MAX_DOWNLOAD_RETRIES,
    MIN_DELAY_BETWEEN_REQUESTS,
    REQUEST_TIMEOUT,
)
from .cache import APICache

logger = logging.getLogger(__name__)


class GutendexAPIClient:
    """Client for interacting with the Gutendex API."""

    BASE_URL = "https://gutendex.com"
    
    def __init__(self, timeout: int = REQUEST_TIMEOUT, use_cache: bool = True, cache_dir: str = ".cache"):
        """Initialize the API client.
        
        Args:
            timeout: Request timeout in seconds
            use_cache: Whether to use caching for API responses
            cache_dir: Directory for cache storage
        """
        self.timeout = timeout
        self.session = httpx.Client(timeout=timeout, follow_redirects=True)
        self.use_cache = use_cache
        self.cache = APICache(cache_dir=cache_dir) if use_cache else None
        logger.info("Initialized Gutendex API client")
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and close session."""
        self.session.close()
    
    def _make_request(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Make a request to the API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # Create cache key from URL and params
        cache_key = url
        if params:
            cache_key += "?" + urlencode(sorted(params.items()))
        
        # Check cache first
        if self.use_cache and self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for: {cache_key}")
                return cached_data
        
        # Make the actual request
        for attempt in range(MAX_DOWNLOAD_RETRIES):
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Cache the successful response
                if self.use_cache and self.cache:
                    self.cache.set(cache_key, data)
                
                return data
            except httpx.HTTPError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{MAX_DOWNLOAD_RETRIES}): {e}")
                if attempt == MAX_DOWNLOAD_RETRIES - 1:
                    raise
    
    def search_books(
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
        
        return self._make_request("/books/", params)
    
    def get_book(self, book_id: int) -> dict[str, Any]:
        """Get details for a specific book.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            Book details
        """
        return self._make_request(f"/books/{book_id}")
    
    def get_popular_books(
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
        # The API doesn't have a direct popularity sort, but we can
        # use the default ordering which tends to show popular books
        results = []
        page = 1
        
        while len(results) < limit:
            response = self.search_books(
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
        
        return results[:limit]
    
    def get_english_books_with_epub(
        self,
        limit: int = 100,
        search: Optional[str] = None,
        topic: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> list[dict[str, Any]]:
        """Get English books that have EPUB format available.
        
        Args:
            limit: Maximum number of books to return
            search: Optional search term
            topic: Optional topic filter
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of books with EPUB format
        """
        from tqdm import tqdm
        
        results = []
        page = 1
        
        # Create progress bar
        pbar = tqdm(total=limit, desc="Fetching books", unit="books", 
                   leave=True, colour="green")
        
        while len(results) < limit:
            response = self.search_books(
                languages=["en"],
                search=search,
                topic=topic,
                page=page,
            )
            
            books = response.get("results", [])
            if not books:
                break
            
            # Filter for books with EPUB format
            books_added = 0
            for book in books:
                formats = book.get("formats", {})
                if any("epub" in fmt.lower() for fmt in formats.keys()):
                    results.append(book)
                    books_added += 1
                    if len(results) >= limit:
                        break
            
            # Update progress
            pbar.update(books_added)
            if progress_callback:
                progress_callback(len(results), limit, page)
            
            # Check if there are more pages
            if not response.get("next"):
                break
            
            page += 1
            pbar.set_description(f"Fetching page {page}")
        
        pbar.close()
        return results
    
    def get_all_english_books_with_epub(
        self,
        search: Optional[str] = None,
        topic: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> list[dict[str, Any]]:
        """Get all English books that have EPUB format available.
        
        Args:
            search: Optional search term
            topic: Optional topic filter
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of all books with EPUB format
        """
        from tqdm import tqdm
        import time
        
        results = []
        page = 1
        start_time = time.time()
        
        # Create indeterminate progress bar since we don't know total
        pbar = tqdm(desc="Discovering books", unit="books", 
                   bar_format='{desc}: {n} {unit} [{elapsed}, {rate_fmt}]',
                   leave=True, colour="cyan")
        
        while True:
            response = self.search_books(
                languages=["en"],
                search=search,
                topic=topic,
                page=page,
            )
            
            books = response.get("results", [])
            if not books:
                break
            
            # Filter for books with EPUB format
            books_added = 0
            for book in books:
                formats = book.get("formats", {})
                if any("epub" in fmt.lower() for fmt in formats.keys()):
                    results.append(book)
                    books_added += 1
            
            # Update progress
            pbar.update(books_added)
            pbar.set_description(f"Page {page} (fetched {len(results)} books)")
            
            if progress_callback:
                progress_callback(len(results), None, page)
            
            # Check if there are more pages
            if not response.get("next"):
                break
            
            page += 1
            
            # Add time estimate based on current rate
            elapsed = time.time() - start_time
            rate = len(results) / elapsed if elapsed > 0 else 0
            logger.info(f"Fetched page {page}, total books: {len(results)} (rate: {rate:.1f} books/sec)")
        
        pbar.close()
        print(f"\nCompleted! Found {len(results)} English books with EPUB format.")
        return results