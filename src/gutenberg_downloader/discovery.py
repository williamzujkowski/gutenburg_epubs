"""Book discovery module for finding English books with EPUB files on Project Gutenberg.

This module provides functionality to discover and filter books based on various criteria
including language, format availability, and book attributes.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Union

from .constants import BASE_URL, ENGLISH_LANGUAGE_CODE
from .epub_downloader import EpubDownloader
from .scraper import GutenbergScraper

logger = logging.getLogger(__name__)


class BookDiscovery:
    """Discovers and filters books from Project Gutenberg."""

    def __init__(
        self,
        scraper: Optional[GutenbergScraper] = None,
        downloader: Optional[EpubDownloader] = None,
    ):
        """Initialize the book discovery system.

        Args:
            scraper: Optional GutenbergScraper instance. If not provided, creates one.
            downloader: Optional EpubDownloader instance. If not provided, creates one.
        """
        self.scraper = scraper or GutenbergScraper()
        self.downloader = downloader or EpubDownloader()

    def __enter__(self) -> "BookDiscovery":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and clean up resources."""
        self.close()

    def close(self) -> None:
        """Close the underlying clients."""
        self.scraper.close()
        self.downloader.close()

    def discover_popular_english_epubs(
        self, limit: int = 100, min_downloads: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Discover popular English books that have EPUB files available.

        Args:
            limit: Maximum number of books to return.
            min_downloads: Minimum download count filter (if available in data).

        Returns:
            List of dictionaries containing book information including EPUB URLs.
        """
        # min_downloads can be used in future enhancements for filtering
        _ = min_downloads
        # Get popular books
        popular_books = self.scraper.get_popular_books(
            limit=limit * 2
        )  # Get more to filter

        english_books_with_epub: list[dict[str, Any]] = []

        for book in popular_books:
            if len(english_books_with_epub) >= limit:
                break

            # Get detailed book information
            book_details = self.get_book_details(book["book_id"])

            if book_details and self._is_english_with_epub(book_details):
                # Add the popular book info to details
                book_details["popularity_rank"] = len(english_books_with_epub) + 1
                book_details["title"] = book.get(
                    "title", book_details.get("metadata", {}).get("title")
                )
                english_books_with_epub.append(book_details)

        return english_books_with_epub

    def get_book_details(
        self, book_id: int, include_formats: bool = True
    ) -> Optional[dict[str, Any]]:
        """Get detailed information about a specific book.

        Args:
            book_id: Project Gutenberg book ID.
            include_formats: Whether to include download format information.

        Returns:
            Dictionary containing book metadata and download links, or None if not found.
        """
        # include_formats can be used in future enhancements for selective parsing
        _ = include_formats
        try:
            book_url = f"{BASE_URL}/ebooks/{book_id}"
            html_content = self.scraper.fetch_page(book_url)

            if not html_content:
                logger.warning(f"Could not fetch book page for ID {book_id}")
                return None

            book_details = self.scraper.parse_book_page(html_content)

            # Ensure book_id is set
            if not book_details.get("book_id"):
                book_details["book_id"] = book_id

            return book_details

        except Exception as e:
            logger.error(f"Error getting details for book {book_id}: {e}")
            return None

    def search_by_title(
        self, title: str, exact_match: bool = False, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search for books by title.

        Args:
            title: Title to search for.
            exact_match: Whether to require exact title match.
            limit: Maximum number of results.

        Returns:
            List of books matching the search criteria.
        """
        # This is a simplified implementation - in reality, you'd want to
        # use Gutenberg's search API or catalog file
        search_results: list[dict[str, Any]] = []

        # Get popular books and filter by title
        popular_books = self.scraper.get_popular_books(limit=1000)

        for book in popular_books:
            if len(search_results) >= limit:
                break

            book_title = book.get("title", "").lower()
            search_term = title.lower()

            if exact_match:
                if book_title == search_term:
                    book_details = self.get_book_details(book["book_id"])
                    if book_details:
                        search_results.append(book_details)
            else:
                if search_term in book_title:
                    book_details = self.get_book_details(book["book_id"])
                    if book_details:
                        search_results.append(book_details)

        return search_results

    def search_by_author(self, author: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for books by author.

        Args:
            author: Author name to search for.
            limit: Maximum number of results.

        Returns:
            List of books by the specified author.
        """
        # This is a simplified implementation
        search_results: list[dict[str, Any]] = []

        # Get popular books and check author information
        popular_books = self.scraper.get_popular_books(limit=1000)

        for book in popular_books:
            if len(search_results) >= limit:
                break

            book_details = self.get_book_details(book["book_id"])

            if book_details:
                book_author = book_details.get("metadata", {}).get("author", "").lower()
                if author.lower() in book_author:
                    search_results.append(book_details)

        return search_results

    def filter_by_language(
        self, books: list[dict[str, Any]], language_code: str = ENGLISH_LANGUAGE_CODE
    ) -> list[dict[str, Any]]:
        """Filter books by language.

        Args:
            books: List of book dictionaries to filter.
            language_code: ISO language code to filter by.

        Returns:
            List of books in the specified language.
        """
        filtered_books = []

        for book in books:
            book_language = book.get("metadata", {}).get("language", "").lower()

            # More strict language matching
            if language_code.lower() == "en":
                # For English, match "en", "eng", "english"
                if book_language == "en" or book_language == "eng" or book_language == "english":
                    filtered_books.append(book)
            else:
                # For other languages, use exact match
                if language_code.lower() == book_language:
                    filtered_books.append(book)

        return filtered_books

    def filter_by_format(
        self, books: list[dict[str, Any]], format_type: str = "epub"
    ) -> list[dict[str, Any]]:
        """Filter books by available format.

        Args:
            books: List of book dictionaries to filter.
            format_type: Format type to filter by (e.g., 'epub', 'pdf', 'txt').

        Returns:
            List of books with the specified format available.
        """
        filtered_books = []

        for book in books:
            download_links = book.get("download_links", {})

            if format_type.lower() in download_links:
                filtered_books.append(book)

        return filtered_books

    def _is_english_with_epub(self, book_details: dict[str, Any]) -> bool:
        """Check if a book is in English and has EPUB available.

        Args:
            book_details: Book details dictionary.

        Returns:
            True if the book is in English and has EPUB format available.
        """
        # Check language - be strict about English matching
        language = book_details.get("metadata", {}).get("language", "").lower()
        is_english = language in ["en", "eng", "english"]

        if not is_english:
            return False

        # Check for EPUB availability
        download_links = book_details.get("download_links", {})
        return "epub" in download_links

    def get_catalog_stats(self) -> dict[str, int]:
        """Get statistics about the Gutenberg catalog.

        Returns:
            Dictionary containing catalog statistics.
        """
        stats = {
            "total_books_sampled": 0,
            "english_books": 0,
            "books_with_epub": 0,
            "english_books_with_epub": 0,
        }

        # Sample popular books for statistics
        sample_size = 1000
        popular_books = self.scraper.get_popular_books(limit=sample_size)

        stats["total_books_sampled"] = len(popular_books)

        for book in popular_books:
            book_details = self.get_book_details(book["book_id"])

            if book_details:
                # Check language - be strict about English matching
                language = book_details.get("metadata", {}).get("language", "").lower()
                is_english = language in ["en", "eng", "english"]

                # Check formats
                has_epub = "epub" in book_details.get("download_links", {})

                if is_english:
                    stats["english_books"] += 1

                if has_epub:
                    stats["books_with_epub"] += 1

                if is_english and has_epub:
                    stats["english_books_with_epub"] += 1

        return stats

    def download_book_epub(
        self,
        book_id: int,
        output_path: Union[str, Path],
        book_details: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Download the EPUB file for a specific book.

        Args:
            book_id: Project Gutenberg book ID.
            output_path: Path where the EPUB should be saved.
            book_details: Optional pre-fetched book details to avoid extra request.

        Returns:
            True if download was successful, False otherwise.
        """
        if not book_details:
            book_details = self.get_book_details(book_id)

        if not book_details:
            logger.error(f"Could not get details for book {book_id}")
            return False

        epub_url = book_details.get("download_links", {}).get("epub")

        if not epub_url:
            logger.error(f"No EPUB URL found for book {book_id}")
            return False

        return self.downloader.download_epub(epub_url, output_path)
