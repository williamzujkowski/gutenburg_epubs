"""Enhanced downloader with advanced filtering and multiple search terms."""

import logging
import os
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set

import httpx
from tqdm import tqdm

from .constants import REQUEST_TIMEOUT, DEFAULT_USER_AGENT, MAX_DOWNLOAD_RETRIES
from .database import BookDatabase
from .smart_downloader import SmartDownloader
from .mirror_manager import MirrorManager

logger = logging.getLogger(__name__)


class EnhancedDownloader(SmartDownloader):
    """Enhanced downloader with multi-filter capabilities."""
    
    def __init__(self, db_path: str = "gutenberg_books.db", mirrors_enabled: bool = False):
        """Initialize enhanced downloader.
        
        Args:
            db_path: Path to the database file
            mirrors_enabled: Whether to use mirror site rotation
        """
        super().__init__(db_path)
        self.mirrors_enabled = mirrors_enabled
        self.mirror_manager = MirrorManager() if mirrors_enabled else None
    
    def search_books_by_filters(
        self,
        search_terms: Optional[List[str]] = None,
        language: Optional[str] = None,
        subjects: Optional[List[str]] = None,
        min_downloads: Optional[int] = None,
        has_epub: bool = True,
        limit: int = 100,
        match_any_term: bool = False
    ) -> List[Dict[str, Any]]:
        """Search for books using multiple filters.
        
        Args:
            search_terms: List of search terms to look for in titles, authors, and subjects
            language: Language code filter (e.g., 'en')
            subjects: List of subjects/genres to filter by
            min_downloads: Minimum download count filter
            has_epub: Only return books with EPUB format
            limit: Maximum number of results to return
            match_any_term: If True, match books that have any of the search terms
                           If False, require all search terms to match (default)
            
        Returns:
            List of matching book dictionaries
        """
        # Initialize full result set
        all_results = []
        
        # If no search terms provided, perform a direct database filter
        if not search_terms:
            # Handle subject filters
            if subjects:
                # Log subject query
                logger.debug(f"Searching for subjects: {subjects}")
                
                # For exact matches, use SQL LIKE with wildcards
                subject_results = []
                for subject in subjects:
                    # Create SQL pattern with wildcards before and after 
                    subject_pattern = f"%{subject}%"
                    logger.debug(f"Using subject pattern: {subject_pattern}")
                    
                    results = self.db.search_books(
                        language=language,
                        subject=subject,  # This will generate a LIKE query
                        min_downloads=min_downloads,
                        has_epub=has_epub,
                        limit=limit * 2  # Get more results to account for filtering
                    )
                    logger.debug(f"Subject '{subject}' found {len(results)} books")
                    subject_results.extend(results)
                
                # If no results with individual subjects, try direct query
                if not subject_results:
                    logger.debug("No results with individual subject queries, trying direct query...")
                    # Use direct SQL query with multiple LIKE conditions
                    with self.db._get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Build a query with multiple LIKE conditions connected with OR
                        like_conditions = []
                        params = []
                        
                        for subject in subjects:
                            like_conditions.append("s.name LIKE ?")
                            params.append(f"%{subject}%")
                        
                        query = f"""
                            SELECT DISTINCT b.* FROM books b
                            JOIN book_subjects bs ON b.book_id = bs.book_id
                            JOIN subjects s ON bs.subject_id = s.subject_id
                            WHERE ({' OR '.join(like_conditions)})
                        """
                        
                        # Add language filter if specified
                        if language:
                            query += " AND b.language = ?"
                            params.append(language)
                            
                        # Add download count filter if specified
                        if min_downloads is not None:
                            query += " AND b.download_count >= ?"
                            params.append(min_downloads)
                            
                        # Add order and limit
                        query += " ORDER BY b.download_count DESC LIMIT ?"
                        params.append(limit)
                        
                        # Execute query
                        logger.debug(f"Executing direct query: {query} with params {params}")
                        cursor.execute(query, params)
                        subject_results = [dict(row) for row in cursor.fetchall()]
                        logger.debug(f"Direct query found {len(subject_results)} books")
                
                # Process results
                if subject_results:
                    # Remove duplicates by book_id
                    seen_ids = set()
                    unique_results = []
                    for book in subject_results:
                        if book['book_id'] not in seen_ids:
                            seen_ids.add(book['book_id'])
                            unique_results.append(book)
                    
                    # Apply limit and enhance results
                    results = unique_results[:limit]
                    # Enhance with additional metadata
                    for book in results:
                        # Get authors
                        if 'authors' not in book:
                            with self.db._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    SELECT a.* FROM authors a
                                    JOIN book_authors ba ON a.author_id = ba.author_id
                                    WHERE ba.book_id = ?
                                """, (book['book_id'],))
                                book['authors'] = [dict(author) for author in cursor.fetchall()]
                        
                        # Get formats
                        if 'formats' not in book:
                            with self.db._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    SELECT format_type, url FROM formats WHERE book_id = ?
                                """, (book['book_id'],))
                                book['formats'] = {row['format_type']: row['url'] 
                                                  for row in cursor.fetchall()}
                    
                    return results
                
                return []
            else:
                # No subjects - just use language and download filters
                return self.db.search_books(
                    language=language,
                    min_downloads=min_downloads,
                    has_epub=has_epub,
                    limit=limit
                )
        
        # Process multiple search terms
        logger.info(f"Searching with terms: {search_terms}")
        if match_any_term:
            # Match ANY term (union of results)
            for term in search_terms:
                results = self.db.full_text_search(term, limit=limit * 2)
                all_results.extend(results)
            
            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for book in all_results:
                if book['book_id'] not in seen_ids:
                    seen_ids.add(book['book_id'])
                    unique_results.append(book)
            
            all_results = unique_results
        else:
            # Match ALL terms (intersection of results)
            if search_terms:
                # Start with results from the first term
                all_results = self.db.full_text_search(search_terms[0], limit=limit * 3)
                
                # Get book IDs to track intersection
                result_ids = {book['book_id'] for book in all_results}
                
                # Filter by remaining terms
                for term in search_terms[1:]:
                    term_results = self.db.full_text_search(term, limit=limit * 3)
                    term_ids = {book['book_id'] for book in term_results}
                    
                    # Intersect with current results
                    result_ids &= term_ids
                
                # Filter all_results to only keep books in the intersection
                all_results = [book for book in all_results if book['book_id'] in result_ids]
        
        # Apply additional filters to search results
        filtered_results = []
        for book in all_results:
            include_book = True
            
            # Apply language filter
            if language and book.get('language') != language:
                include_book = False
            
            # Apply subject filters if needed
            if subjects and include_book:
                book_subjects = set(book.get('subjects', []))
                
                # Check if any of the requested subjects match (with partial matching)
                matched = False
                for req_subject in subjects:
                    for book_subject in book_subjects:
                        if req_subject.lower() in book_subject.lower():
                            matched = True
                            break
                    if matched:
                        break
                        
                if not matched:
                    include_book = False
            
            # Apply download count filter
            if min_downloads is not None and include_book:
                if book.get('download_count', 0) < min_downloads:
                    include_book = False
            
            # Apply EPUB format filter
            if has_epub and include_book:
                has_epub_format = False
                for format_type in book.get('formats', {}).keys():
                    if 'epub' in format_type.lower():
                        has_epub_format = True
                        break
                
                if not has_epub_format:
                    include_book = False
            
            if include_book:
                filtered_results.append(book)
            
            # Stop if we have enough results
            if len(filtered_results) >= limit:
                break
        
        return filtered_results[:limit]
    
    def search_and_download(
        self,
        search_terms: Optional[Union[str, List[str]]] = None,
        language: str = "en",
        subjects: Optional[Union[str, List[str]]] = None,
        min_downloads: Optional[int] = None,
        output_dir: Path = Path("downloads"),
        limit: int = 10,
        match_any_term: bool = False,
        skip_existing: bool = True,
        resume: bool = True,
        force_download: bool = False
    ) -> Tuple[int, int]:
        """Search for books using multiple filters and download them.
        
        Args:
            search_terms: List of search terms to look for in titles, authors, and subjects
            language: Language code filter (e.g., 'en')
            subjects: List of subjects/genres to filter by
            min_downloads: Minimum download count filter
            output_dir: Directory to save downloaded books
            limit: Maximum number of books to download
            match_any_term: If True, match books that have any of the search terms
                           If False, require all search terms to match (default)
            skip_existing: Skip books that already exist in the output directory
            resume: Enable resume capability for interrupted downloads
            force_download: Force download even if files already exist (useful for testing mirror fallback)
            
        Returns:
            Tuple of (successfully downloaded count, failed count)
        """
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse the input parameters to handle string input
        if search_terms and isinstance(search_terms, str):
            search_terms = self.normalize_search_terms(search_terms)
            logger.debug(f"Normalized search terms: {search_terms}")
        
        if subjects and isinstance(subjects, str):
            subjects = self.normalize_subjects(subjects)
            logger.debug(f"Normalized subjects: {subjects}")
            
        # Find matching books
        books = self.search_books_by_filters(
            search_terms=search_terms,
            language=language,
            subjects=subjects,
            min_downloads=min_downloads,
            has_epub=True,
            limit=limit,
            match_any_term=match_any_term
        )
        
        logger.debug(f"Found {len(books)} books matching filters")
        
        if not books:
            logger.info("No matching books found.")
            return 0, 0
        
        logger.info(f"Found {len(books)} matching books. Starting downloads...")
        
        # Download books
        success_count = 0
        failed_count = 0
        
        for i, book in enumerate(books, 1):
            book_id = book.get('book_id')
            title = book.get('title', f'book_{book_id}')
            
            # Generate filename
            clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            clean_title = clean_title.replace(" ", "_")[:100]  # Limit length
            filename = f"{clean_title}.epub"
            output_path = output_dir / filename
            
            # Check for existing file
            if skip_existing and output_path.exists() and not force_download:
                logger.info(f"Skipping {book_id}: {title} (already exists)")
                success_count += 1  # Count as success since it exists
                continue
            
            # If force_download is enabled, remove the existing file to force a fresh download
            if force_download and output_path.exists():
                logger.info(f"Force download enabled. Removing existing file: {output_path}")
                output_path.unlink()
            
            # Find EPUB URL from book data
            epub_url = None
            for format_type, url in book.get('formats', {}).items():
                if 'epub' in format_type.lower():
                    epub_url = url
                    break
            
            # If no EPUB URL found in database, try API
            if not epub_url:
                logger.info(f"No EPUB URL found in database for book {book_id}. Trying API...")
                
                # Try using API discovery 
                from .api_discovery import APIBookDiscovery
                
                try:
                    with APIBookDiscovery() as api:
                        # Get book details from API
                        api_book = api.get_book_by_id(book_id)
                        
                        if api_book and 'download_links' in api_book:
                            # Find EPUB URL
                            epub_url = api_book['download_links'].get('epub')
                            
                            # If found, store in database for future use
                            if epub_url:
                                logger.info(f"Found EPUB URL from API for book {book_id}")
                                # Add format to database
                                with self.db._get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO formats 
                                        (book_id, format_type, url, mime_type)
                                        VALUES (?, ?, ?, ?)
                                    """, (book_id, 'application/epub+zip', epub_url, 'application/epub+zip'))
                                    conn.commit()
                except Exception as e:
                    logger.error(f"Error getting book details from API: {e}")
            
            # If still no EPUB URL, try Project Gutenberg URL pattern
            if not epub_url:
                logger.info(f"Trying standard Gutenberg URL pattern for book {book_id}...")
                epub_url = f"https://www.gutenberg.org/ebooks/{book_id}.epub"
                
            # Check if we have a URL to try
            if not epub_url:
                logger.error(f"No EPUB format available for book {book_id}: {title}")
                failed_count += 1
                continue
            
            # Download the book
            logger.info(f"Downloading [{i}/{len(books)}] {book_id}: {title}")
            
            success = self.download_book(
                book_id,
                epub_url, 
                output_dir,
                filename=filename,
                resume=resume
            )
            
            if success:
                success_count += 1
                logger.info(f"Successfully downloaded to {output_path}")
            else:
                failed_count += 1
                logger.error(f"Failed to download book {book_id}")
        
        return success_count, failed_count
    
    def normalize_search_terms(self, search_terms: Union[str, List[str]]) -> List[str]:
        """Normalize and clean search terms.
        
        Args:
            search_terms: Single string or list of search terms
            
        Returns:
            List of normalized search terms
        """
        if isinstance(search_terms, str):
            # Preserve quoted terms (like "science fiction")
            quoted_terms = re.findall(r'"([^"]+)"', search_terms)
            
            # Remove quoted sections to process commas separately
            no_quotes = re.sub(r'"[^"]+"', '', search_terms)
            
            # Process comma-separated terms
            comma_terms = [term.strip() for term in no_quotes.split(',') if term.strip()]
            
            # Combine all terms
            terms = quoted_terms + comma_terms
        else:
            # Already a list, just clean up
            terms = [term.strip('"\'') for term in search_terms]
        
        # Remove empty terms
        return [term for term in terms if term]
    
    def normalize_subjects(self, subjects: Union[str, List[str]]) -> List[str]:
        """Normalize subject/genre list and handle common aliases.
        
        Args:
            subjects: Single string or list of subjects
            
        Returns:
            List of normalized subjects with aliases expanded
        """
        # First normalize terms
        normalized = self.normalize_search_terms(subjects)
        
        # Handle common aliases and variations
        expanded = []
        aliases = {
            "scifi": ["science fiction"],
            "sci-fi": ["science fiction"],
            "sf": ["science fiction"],
            "sci fi": ["science fiction"],
            "science-fiction": ["science fiction"],
            
            "fantasy": ["fantasy"], 
            "adventure": ["adventure"],
            "mystery": ["mystery", "detective"],
            "detective": ["detective", "mystery"],
            "horror": ["horror", "gothic"],
            "romance": ["romance", "love stories"],
            "western": ["western", "cowboys", "frontier"],
            "historical": ["historical", "history"],
            "biography": ["biography", "autobiography", "memoirs"],
            "autobiography": ["autobiography", "biography"],
            "poetry": ["poetry", "poems"],
            "drama": ["drama", "plays"],
            "philosophy": ["philosophy", "philosophical"],
            "religion": ["religion", "religious"],
            "politics": ["politics", "political"],
            "classic": ["classic", "classics"]
        }
        
        # Expand all terms with their aliases
        for term in normalized:
            term_lower = term.lower()
            # Add the original term
            expanded.append(term)
            
            # Add any aliases
            if term_lower in aliases:
                expanded.extend(aliases[term_lower])
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for term in expanded:
            if term.lower() not in seen:
                seen.add(term.lower())
                result.append(term)
                
        return result