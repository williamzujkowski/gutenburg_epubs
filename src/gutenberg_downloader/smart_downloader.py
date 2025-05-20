"""Smart downloader with resume capability and failure recovery."""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

import httpx
from tqdm import tqdm

from .constants import REQUEST_TIMEOUT, DEFAULT_USER_AGENT, MAX_DOWNLOAD_RETRIES
from .database import BookDatabase
from .mirror_manager import MirrorManager

logger = logging.getLogger(__name__)


class SmartDownloader:
    """Smart downloader with resume capability and state tracking."""
    
    def __init__(self, db_path: str = "gutenberg_books.db", mirrors_enabled: bool = False):
        """Initialize smart downloader.
        
        Args:
            db_path: Path to the database file
            mirrors_enabled: Whether to use mirror site rotation
        """
        self.db = BookDatabase(db_path)
        self.mirrors_enabled = mirrors_enabled
        self.mirror_manager = MirrorManager() if mirrors_enabled else None
        self.client = httpx.Client(
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True  # Add this to follow redirects
        )
        
    def __enter__(self) -> "SmartDownloader":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        """Context manager exit."""
        self.client.close()
        if self.mirror_manager:
            self.mirror_manager.close()
    
    def get_download_state(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get download state for a book.
        
        Args:
            book_id: Book ID
            
        Returns:
            Download state or None
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM downloads 
                WHERE book_id = ? 
                ORDER BY download_date DESC 
                LIMIT 1
            """, (book_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_download_state(
        self, 
        book_id: int, 
        status: str, 
        download_path: Optional[str] = None,
        bytes_downloaded: int = 0,
        total_bytes: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """Update download state in database.
        
        Args:
            book_id: Book ID
            status: Download status ('pending', 'downloading', 'completed', 'failed')
            download_path: Path to download file
            bytes_downloaded: Bytes downloaded so far
            total_bytes: Total file size
            error_message: Error message if failed
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute("""
                SELECT download_id FROM downloads 
                WHERE book_id = ? AND download_path = ?
            """, (book_id, download_path))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE downloads 
                    SET status = ?, 
                        bytes_downloaded = ?, 
                        total_bytes = ?,
                        error_message = ?,
                        download_date = CURRENT_TIMESTAMP
                    WHERE book_id = ? AND download_path = ?
                """, (
                    status, 
                    bytes_downloaded, 
                    total_bytes, 
                    error_message,
                    book_id, 
                    download_path
                ))
            else:
                # Create new record
                cursor.execute("""
                    INSERT INTO downloads (
                        book_id, download_path, status, 
                        bytes_downloaded, total_bytes, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    book_id, 
                    download_path, 
                    status, 
                    bytes_downloaded, 
                    total_bytes, 
                    error_message
                ))
                
            conn.commit()
    
    def download_with_resume(
        self, 
        url: str, 
        output_path: Path, 
        book_id: Optional[int] = None,
        enable_resume: bool = True
    ) -> bool:
        """Download a file with resume capability.
        
        Args:
            url: URL to download
            output_path: Path to save the file
            book_id: Optional book ID for state tracking
            enable_resume: Whether to enable resume capability for interrupted downloads
            
        Returns:
            True if successful, False otherwise
        """
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup for resume
        retries = 0
        resume_pos = 0
        
        if enable_resume and output_path.exists():
            resume_pos = output_path.stat().st_size
            if resume_pos > 0:
                logger.info(f"Found existing file {output_path.name} with {resume_pos} bytes. Attempting to resume from that position.")
        elif output_path.exists():
            # Delete existing file when resume is disabled but file exists
            output_path.unlink()
            logger.info(f"Deleting existing file {output_path.name} as resume is disabled.")
        
        # Use mirror sites if enabled and book_id is provided
        mirror_url = None
        if self.mirrors_enabled and self.mirror_manager and book_id:
            mirror_url = self.mirror_manager.get_book_url(book_id)
            if mirror_url:
                logger.info(f"Using mirror for book {book_id}: {mirror_url}")
                url = mirror_url
        
        while retries < MAX_DOWNLOAD_RETRIES:
            try:
                # Setup headers for resume
                headers = {}
                if enable_resume and resume_pos > 0:
                    headers['Range'] = f'bytes={resume_pos}-'
                
                # Make request using stream context manager
                with self.client.stream("GET", url, headers=headers) as response:
                    # Check if server supports resume when needed
                    if enable_resume and resume_pos > 0 and response.status_code != 206:
                        logger.warning("Server doesn't support resume, starting from beginning")
                        resume_pos = 0
                        response.close()
                        with self.client.stream("GET", url) as response:
                            return self._process_download_response(
                                response, book_id, output_path, resume_pos, enable_resume)
                    
                    return self._process_download_response(response, book_id, output_path, resume_pos, enable_resume)
            
            except Exception as e:
                retries += 1
                error_msg = f"Download error (attempt {retries}/{MAX_DOWNLOAD_RETRIES}): {e}"
                logger.error(error_msg)
                
                if book_id:
                    self.update_download_state(
                        book_id,
                        'failed' if retries >= MAX_DOWNLOAD_RETRIES else 'downloading',
                        str(output_path),
                        output_path.stat().st_size if output_path.exists() else 0,
                        error_message=str(e)
                    )
                
                # If using mirrors, report failure and try a different mirror
                if self.mirrors_enabled and self.mirror_manager and book_id and mirror_url:
                    self.mirror_manager.report_failure(mirror_url)
                    # Get a new mirror URL for the next attempt
                    new_mirror_url = self.mirror_manager.get_book_url(book_id)
                    if new_mirror_url and new_mirror_url != mirror_url:
                        logger.info(f"Switching to alternate mirror: {new_mirror_url}")
                        url = new_mirror_url
                        mirror_url = new_mirror_url
                
                if retries < MAX_DOWNLOAD_RETRIES:
                    time.sleep(2 ** retries)  # Exponential backoff
                    resume_pos = output_path.stat().st_size if output_path.exists() else 0
        
        return False
    
    def _process_download_response(self, response, book_id, output_path, resume_pos, enable_resume=True):
        """Process download response and save the file.
        
        Args:
            response: HTTP response object
            book_id: Book ID or None
            output_path: Output file path
            resume_pos: Position to resume from
            enable_resume: Whether resume capability is enabled
            
        Returns:
            True if successful, False otherwise
            
        Notes:
            This method handles 404 errors specially, attempting to retry with different mirrors
            when a 404 Not Found error is encountered. This way, if one mirror doesn't have a
            specific book, the system will automatically try other mirrors until it finds one
            that does have the book.
        """
        try:
            # Check for 404 status - special handling for this error
            if response.status_code == 404:
                logger.warning(f"Received 404 Not Found for URL: {response.url}")
                
                # If we're using mirrors and have a book_id, try another mirror instead of failing
                if self.mirrors_enabled and self.mirror_manager and book_id:
                    # Report failure to mirror manager
                    current_url = str(response.url)
                    hostname = response.url.host
                    base_url = f"{response.url.scheme}://{hostname}"
                    self.mirror_manager.report_failure(base_url)
                    
                    # Get a new URL from a different mirror
                    logger.info(f"Attempting to find an alternate mirror for book {book_id} after 404 error")
                    
                    # Explicitly exclude the current mirror that returned a 404
                    self.mirror_manager.recently_used.append(base_url)
                    
                    # Get a fresh URL from a different mirror
                    new_mirror_url = self.mirror_manager.select_mirror(book_id)
                    new_book_url = self.mirror_manager.build_book_url(book_id, new_mirror_url)
                    
                    # Only retry if we got a different URL
                    if new_book_url != current_url:
                        logger.info(f"Retrying with alternative mirror: {new_book_url}")
                        # Recursively call download with the new URL
                        return self.download_with_resume(new_book_url, output_path, book_id, enable_resume)
                    else:
                        logger.warning("No alternative mirrors available, or all mirrors returned 404")
                
                # If we can't retry with a different mirror, then fail
                return False
            
            # For other status codes, raise for status as before
            response.raise_for_status()
            
            # Get total size
            total_size = int(response.headers.get('content-length', 0))
            if resume_pos > 0:
                total_size += resume_pos
            
            # Download with progress - use append mode for resume, write mode otherwise
            mode = 'ab' if enable_resume and resume_pos > 0 else 'wb'
            with open(output_path, mode) as f:
                with tqdm(
                    total=total_size,
                    initial=resume_pos,
                    unit='B',
                    unit_scale=True,
                    desc=f"Downloading {output_path.name}"
                ) as pbar:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
                        
                        # Update state periodically
                        if book_id and pbar.n % (1024 * 1024) == 0:  # Every 1MB
                            self.update_download_state(
                                book_id,
                                'downloading',
                                str(output_path),
                                pbar.n,
                                total_size
                            )
            
            # Mark as completed
            if book_id:
                self.update_download_state(
                    book_id,
                    'completed',
                    str(output_path),
                    total_size,
                    total_size
                )
                
                # If using mirrors, report success
                if self.mirrors_enabled and self.mirror_manager:
                    # Get the hostname from the response URL
                    hostname = response.url.host
                    base_url = f"{response.url.scheme}://{hostname}"
                    self.mirror_manager.report_success(base_url)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing download: {e}")
            
            # Special handling for other HTTP errors if using mirrors
            if isinstance(e, httpx.HTTPStatusError) and self.mirrors_enabled and self.mirror_manager and book_id:
                status_code = e.response.status_code
                logger.warning(f"HTTP error {status_code} for URL: {e.response.url}")
                
                # Report failure to mirror manager
                hostname = e.response.url.host
                base_url = f"{e.response.url.scheme}://{hostname}"
                self.mirror_manager.report_failure(base_url)
                
                # For client errors (4xx), try another mirror
                if 400 <= status_code < 500:
                    logger.info(f"Attempting to find an alternate mirror for book {book_id} after {status_code} error")
                    
                    # Explicitly exclude the current mirror
                    current_url = str(e.response.url)
                    self.mirror_manager.recently_used.append(base_url)
                    
                    # Get a fresh URL from a different mirror
                    new_mirror_url = self.mirror_manager.select_mirror(book_id)
                    new_book_url = self.mirror_manager.build_book_url(book_id, new_mirror_url)
                    
                    # Only retry if we got a different URL
                    if new_book_url != current_url:
                        logger.info(f"Retrying with alternative mirror: {new_book_url}")
                        # Recursively call download with the new URL
                        return self.download_with_resume(new_book_url, output_path, book_id, enable_resume)
            
            return False
    
    def download_book(
        self,
        book_id: int,
        epub_url: str,
        output_dir: Path,
        filename: Optional[str] = None,
        resume: bool = True
    ) -> bool:
        """Download a book with smart resume.
        
        Args:
            book_id: Book ID
            epub_url: URL to EPUB file
            output_dir: Output directory
            filename: Optional custom filename
            resume: Whether to enable resume capability for interrupted downloads
            
        Returns:
            True if successful, False otherwise
        """
        # Get book metadata
        book = self.db.get_book(book_id)
        if not book:
            logger.error(f"Book {book_id} not found in database")
            return False
        
        # Determine filename
        if not filename:
            title = book.get('title', f'book_{book_id}')
            clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            clean_title = clean_title.replace(" ", "_")[:100]  # Limit length
            filename = f"{clean_title}.epub"
        
        output_path = output_dir / filename
        
        # Check if already completed
        state = self.get_download_state(book_id)
        if state and state['status'] == 'completed' and output_path.exists():
            logger.info(f"Book {book_id} already downloaded to {output_path}")
            return True
        
        # Download with resume if enabled
        return self.download_with_resume(epub_url, output_path, book_id, enable_resume=resume)
    
    def get_pending_downloads(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of pending downloads.
        
        Args:
            limit: Optional limit on number of results
            
        Returns:
            List of pending download records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT d.*, b.title 
                FROM downloads d
                JOIN books b ON d.book_id = b.book_id
                WHERE d.status IN ('pending', 'downloading', 'failed')
                ORDER BY d.download_date DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def resume_all_downloads(self, output_dir: Path) -> Tuple[int, int]:
        """Resume all pending downloads.
        
        Args:
            output_dir: Output directory
            
        Returns:
            Tuple of (successful, failed) counts
        """
        pending = self.get_pending_downloads()
        
        if not pending:
            logger.info("No pending downloads to resume")
            return 0, 0
        
        logger.info(f"Resuming {len(pending)} downloads...")
        
        successful = 0
        failed = 0
        
        for download in pending:
            book_id = download['book_id']
            download_path = Path(download['download_path'])
            
            # Get book data
            book = self.db.get_book(book_id)
            if not book:
                logger.error(f"Book {book_id} not found in database")
                failed += 1
                continue
            
            # Find EPUB URL
            epub_url = None
            for format_type, url in book.get('formats', {}).items():
                if 'epub' in format_type.lower():
                    epub_url = url
                    break
                    
            if not epub_url:
                logger.error(f"No EPUB URL found for book {book_id}")
                failed += 1
                continue
            
            # Ensure output directory exists
            output_path = output_dir / download_path.name
            
            logger.info(f"Resuming download of {book['title']} ({book_id}) to {output_path}")
            
            # Download with resume
            success = self.download_with_resume(epub_url, output_path, book_id)
            
            if success:
                successful += 1
            else:
                failed += 1
        
        return successful, failed
    
    def clean_up_failed_downloads(self) -> int:
        """Clean up failed download records.
        
        Returns:
            Number of records cleaned up
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM downloads
                WHERE status = 'failed'
            """)
            
            count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {count} failed download records")
            return count
            
    def verify_downloads(self, output_dir: Path) -> Tuple[int, int, int]:
        """Verify downloads against database records.
        
        Args:
            output_dir: Directory containing downloads
            
        Returns:
            Tuple of (verified, missing, corrupted) counts
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.*, b.title 
                FROM downloads d
                JOIN books b ON d.book_id = b.book_id
                WHERE d.status = 'completed'
            """)
            
            completed = [dict(row) for row in cursor.fetchall()]
            
        verified = 0
        missing = 0
        corrupted = 0
        
        for download in completed:
            download_path = Path(download['download_path'])
            
            # Check if using absolute paths or relative to output_dir
            if not download_path.is_absolute():
                file_path = output_dir / download_path
            else:
                file_path = download_path
                
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"Missing file: {file_path}")
                missing += 1
                continue
                
            # Verify file size
            actual_size = file_path.stat().st_size
            expected_size = download['total_bytes']
            
            if actual_size != expected_size:
                logger.warning(
                    f"Size mismatch for {file_path}: "
                    f"expected {expected_size}, got {actual_size}"
                )
                corrupted += 1
            else:
                verified += 1
                
        return verified, missing, corrupted