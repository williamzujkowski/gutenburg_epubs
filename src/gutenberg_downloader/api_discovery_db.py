"""Book discovery service using the Gutendex API with database integration."""

import logging
from typing import Any, Optional

from .api_client import GutendexAPIClient
from .epub_downloader import EpubDownloader
from .database import BookDatabase

logger = logging.getLogger(__name__)


class APIBookDiscoveryDB:
    """Service for discovering books via the Gutendex API with database integration."""
    
    def __init__(self, db_path: str = "gutenberg_books.db", use_cache: bool = True):
        """Initialize the discovery service.
        
        Args:
            db_path: Path to the SQLite database
            use_cache: Whether to use API caching
        """
        self.api_client = GutendexAPIClient(use_cache=use_cache)
        self.downloader = EpubDownloader()
        self.db = BookDatabase(db_path)
        logger.info("Initialized API-based book discovery with database")
    
    def __enter__(self):
        """Enter context manager."""
        self.api_client.__enter__()
        self.downloader.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.api_client.__exit__(exc_type, exc_val, exc_tb)
        self.downloader.__exit__(exc_type, exc_val, exc_tb)
    
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
    
    def discover_popular_english_epubs(
        self,
        limit: int = 100,
        min_downloads: Optional[int] = None,
        get_all: bool = False,
        refresh_db: bool = False,
    ) -> list[dict[str, Any]]:
        """Discover popular English books with EPUB files.
        
        Args:
            limit: Maximum number of books to return (ignored if get_all=True)
            min_downloads: Minimum download count (if supported by API)
            get_all: Whether to get all available books
            refresh_db: Whether to refresh the database from API
            
        Returns:
            List of book dictionaries with metadata
        """
        # Check database first if not refreshing
        if not refresh_db:
            db_books = self.db.get_popular_english_epubs(limit)
            if db_books:
                logger.info(f"Found {len(db_books)} books in database")
                return db_books
        
        try:
            if get_all:
                logger.info("Discovering all English EPUB books via API")
                print("\n🔍 Discovering all English EPUB books from Project Gutenberg...")
                print("This may take several minutes depending on your connection.\n")
                api_books = self.api_client.get_all_english_books_with_epub()
            else:
                logger.info(f"Discovering up to {limit} popular English EPUB books via API")
                print(f"\n📚 Fetching up to {limit} English EPUB books from Project Gutenberg...\n")
                api_books = self.api_client.get_english_books_with_epub(limit=limit)
            
            # Store in database with progress
            print(f"\n💾 Storing {len(api_books)} books in database...")
            from tqdm import tqdm
            
            # Create progress bar for database storage
            with tqdm(total=len(api_books), desc="Storing in database", unit="books", 
                     leave=True, colour="yellow") as pbar:
                stored_count = self.db.bulk_insert_books(api_books)
                pbar.update(stored_count)
            
            logger.info(f"Stored {stored_count} books in database")
            
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
            # Fall back to database if available
            db_books = self.db.get_popular_english_epubs(limit)
            if db_books:
                logger.info(f"Falling back to {len(db_books)} books from database")
                return db_books
            return []
    
    def search_by_title(
        self,
        title: str,
        exact_match: bool = False,
        limit: int = 50,
        use_db: bool = True,
    ) -> list[dict[str, Any]]:
        """Search for books by title.
        
        Args:
            title: Title to search for
            exact_match: Whether to require exact title match
            limit: Maximum number of results
            use_db: Whether to search database first
            
        Returns:
            List of matching books
        """
        # Search database first if enabled
        if use_db:
            db_results = self.db.search_books(title=title, limit=limit)
            if db_results:
                logger.info(f"Found {len(db_results)} books in database")
                return db_results
        
        try:
            logger.info(f"Searching for books with title: {title}")
            
            api_books = self.api_client.get_english_books_with_epub(
                limit=limit,
                search=title
            )
            
            # Store new books in database
            self.db.bulk_insert_books(api_books)
            
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
    
    def search_by_author(
        self,
        author: str,
        limit: int = 50,
        use_db: bool = True,
    ) -> list[dict[str, Any]]:
        """Search for books by author.
        
        Args:
            author: Author name to search for
            limit: Maximum number of results
            use_db: Whether to search database first
            
        Returns:
            List of matching books
        """
        # Search database first if enabled
        if use_db:
            db_results = self.db.search_books(author=author, limit=limit)
            if db_results:
                logger.info(f"Found {len(db_results)} books in database")
                return db_results
        
        try:
            logger.info(f"Searching for books by author: {author}")
            
            api_books = self.api_client.get_english_books_with_epub(
                limit=limit,
                search=author
            )
            
            # Store new books in database
            self.db.bulk_insert_books(api_books)
            
            formatted_books = []
            for api_book in api_books:
                book_data = self._format_book_data(api_book)
                formatted_books.append(book_data)
            
            logger.info(f"Found {len(formatted_books)} books by author: {author}")
            return formatted_books
            
        except Exception as e:
            logger.error(f"Error searching by author: {e}")
            return []
    
    def get_book_by_id(self, book_id: int) -> Optional[dict[str, Any]]:
        """Get book details by Project Gutenberg ID.
        
        Args:
            book_id: Project Gutenberg book ID
            
        Returns:
            Book details or None if not found
        """
        # Check database first
        db_book = self.db.get_book(book_id)
        if db_book:
            logger.info(f"Found book {book_id} in database")
            return db_book
        
        try:
            logger.info(f"Getting book details for ID: {book_id}")
            
            api_book = self.api_client.get_book(book_id)
            
            # Store in database
            self.db.insert_book(api_book)
            
            book_data = self._format_book_data(api_book)
            return book_data
            
        except Exception as e:
            logger.error(f"Error getting book {book_id}: {e}")
            return None
    
    def download_book(
        self,
        book_id: int,
        output_path: str,
        book_details: Optional[dict[str, Any]] = None,
        check_downloaded: bool = True,
    ) -> bool:
        """Download a book by its ID.
        
        Args:
            book_id: Project Gutenberg book ID
            output_path: Output file path
            book_details: Optional pre-fetched book details
            check_downloaded: Whether to check if already downloaded
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already downloaded
            if check_downloaded and self.db.is_downloaded(book_id):
                logger.info(f"Book {book_id} already downloaded")
                return True
            
            # Get book details if not provided
            if not book_details:
                book_details = self.get_book_by_id(book_id)
                
            if not book_details:
                logger.error(f"Book {book_id} not found")
                return False
            
            epub_url = book_details.get("download_links", {}).get("epub")
            if not epub_url:
                logger.error(f"No EPUB URL found for book {book_id}")
                return False
            
            # Download the EPUB
            success = self.downloader.download_epub(epub_url, output_path)
            
            if success:
                # Mark as downloaded in database
                file_size = 0
                try:
                    import os
                    file_size = os.path.getsize(output_path)
                except:
                    pass
                
                self.db.mark_downloaded(book_id, output_path, file_size)
            
            return success
            
        except Exception as e:
            logger.error(f"Error downloading book {book_id}: {e}")
            return False
    
    def get_database_stats(self) -> dict[str, Any]:
        """Get statistics from the database.
        
        Returns:
            Database statistics
        """
        return self.db.get_statistics()