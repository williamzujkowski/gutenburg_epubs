"""EPUB downloader module for downloading EPUB files from Project Gutenberg.

This module provides functionality to download EPUB files with proper error handling,
progress tracking, file management, and resume capabilities for interrupted downloads.
"""

import logging
import os
import time
from pathlib import Path
from typing import IO, Any, Callable, Dict, List, Optional, Union

import httpx
from tqdm import tqdm

from .constants import DEFAULT_USER_AGENT, REQUEST_TIMEOUT
from .mirror_manager import MirrorManager

logger = logging.getLogger(__name__)


class EpubDownloader:
    """Handles downloading of EPUB files from Project Gutenberg."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = REQUEST_TIMEOUT,
        chunk_size: int = 8192,
        mirrors_enabled: bool = True,
    ):
        """Initialize the EPUB downloader.

        Args:
            user_agent: User agent string for HTTP requests.
            timeout: Timeout in seconds for HTTP requests.
            chunk_size: Size of chunks to read/write during download.
            mirrors_enabled: Whether to use mirror sites for downloads.
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.mirrors_enabled = mirrors_enabled
        self.client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
        )
        
        # Initialize mirror manager if mirrors are enabled
        self.mirror_manager = None
        if mirrors_enabled:
            self.mirror_manager = MirrorManager(user_agent=user_agent, timeout=timeout)

    def __enter__(self) -> "EpubDownloader":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and clean up resources."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
        if self.mirror_manager:
            self.mirror_manager.close()

    def _handle_download_response(
        self,
        response: httpx.Response,
        output_path: Path,
        mode: str,
        existing_size: int,
        file_size: Optional[int],
        progress_bar: bool,
        verify_size: bool,
        resume: bool,
        url: str
    ) -> bool:
        """Handle the download response stream.
        
        Args:
            response: The HTTP response object
            output_path: Path to save the file
            mode: File open mode (wb or ab)
            existing_size: Existing file size for resume
            file_size: Known file size from HEAD request or None
            progress_bar: Whether to display progress bar
            verify_size: Whether to verify file size
            resume: Whether resume is enabled
            url: Original URL for error reporting
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check response status
            response.raise_for_status()
            
            # Get content length from GET response
            if response.status_code == 206:  # Partial content
                # For resumed downloads, add the existing size to the new content length
                current_size = int(response.headers.get("content-length", 0))
                file_size = existing_size + current_size
            elif file_size is None:
                file_size = int(response.headers.get("content-length", 0))

            # Setup progress bar if requested
            progress = None
            if progress_bar and file_size > 0:
                progress = tqdm(
                    total=file_size,
                    initial=existing_size,  # Start from existing size
                    unit="B",
                    unit_scale=True,
                    desc=output_path.name,
                )

            # Download and write the file
            downloaded_size = existing_size
            with open(output_path, mode) as file:
                for chunk in response.iter_bytes(chunk_size=self.chunk_size):
                    file.write(chunk)
                    downloaded_size += len(chunk)

                    if progress:
                        progress.update(len(chunk))

            if progress:
                progress.close()
                
            # Verify the downloaded file size
            if verify_size and file_size > 0 and downloaded_size != file_size:
                logger.error(
                    f"Downloaded size ({downloaded_size}) doesn't match "
                    f"expected size ({file_size}) for {url}"
                )
                # Don't remove the file if we're resuming - keep the partial download
                if not resume:
                    output_path.unlink()
                return False

            logger.info(f"Successfully downloaded {url} to {output_path}")
            
            # Report success to mirror manager if appropriate
            if self.mirror_manager and self.mirrors_enabled:
                # Extract the base URL from the full URL
                parsed_url = httpx.URL(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.host}"
                self.mirror_manager.report_success(base_url)
                
            return True
            
        except Exception as e:
            logger.error(f"Error handling download response: {e}")
            return False

    def _get_download_url(self, book_id: int, original_url: str) -> str:
        """Get the download URL, potentially using a mirror site.
        
        Args:
            book_id: The book ID
            original_url: The original URL to download from
            
        Returns:
            The URL to use for downloading
        """
        if not self.mirrors_enabled or not self.mirror_manager:
            return original_url
        
        # Extract book_id from the URL if not provided
        if book_id <= 0:
            try:
                # Try to extract book ID from URL
                path_parts = httpx.URL(original_url).path.strip("/").split("/")
                for part in path_parts:
                    if part.isdigit():
                        book_id = int(part)
                        break
                    elif part.endswith(".epub") and part.startswith("pg"):
                        # Handle format like "pg12345.epub"
                        book_id_str = part[2:].split(".")[0]
                        if book_id_str.isdigit():
                            book_id = int(book_id_str)
                            break
            except (ValueError, IndexError):
                # If we can't extract the book ID, just use the original URL
                return original_url
        
        if book_id > 0:
            mirror_url = self.mirror_manager.get_book_url(book_id)
            logger.info(f"Using mirror URL: {mirror_url} instead of {original_url}")
            return mirror_url
        
        return original_url

    def download_epub(
        self,
        url: str,
        output_path: Union[str, Path],
        progress_bar: bool = True,
        verify_size: bool = True,
        resume: bool = True,
        book_id: int = 0,
    ) -> bool:
        """Download an EPUB file from the given URL with resume capabilities.

        Args:
            url: URL of the EPUB file to download.
            output_path: Path where the EPUB file should be saved.
            progress_bar: Whether to show a progress bar during download.
            verify_size: Whether to verify the downloaded file size.
            resume: Whether to attempt to resume if file exists.
            book_id: Optional book ID for mirror selection (extracted from URL if not provided).

        Returns:
            True if download was successful, False otherwise.

        Raises:
            httpx.HTTPError: If there's an error during the HTTP request.
            IOError: If there's an error writing the file.
        """
        output_path = Path(output_path)

        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if we can resume
        existing_size = 0
        mode = "wb"
        
        if resume and output_path.exists():
            existing_size = output_path.stat().st_size
            if existing_size > 0:
                logger.info(f"Found existing file {output_path.name} with {existing_size} bytes. Attempting to resume.")
                mode = "ab"  # Append mode for resume

        # Get the download URL (possibly from a mirror)
        download_url = self._get_download_url(book_id, url)
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # First, get the file size with a HEAD request
                file_size = None
                if verify_size or progress_bar:
                    try:
                        head_response = self.client.head(download_url)
                        head_response.raise_for_status()
                        file_size = int(head_response.headers.get("content-length", 0))
                    except (httpx.HTTPError, ValueError):
                        logger.warning(f"Could not determine file size for {download_url}")
                
                # Set up headers for resume if needed
                headers = {}
                if existing_size > 0:
                    headers["Range"] = f"bytes={existing_size}-"
                    
                # Download the file
                # Create the initial request
                request_headers = headers if existing_size > 0 else {}
                
                # Use the streaming request within a proper with statement
                with self.client.stream("GET", download_url, headers=request_headers) as response:
                    # Check if server supports resume
                    if existing_size > 0:
                        if response.status_code == 206:  # Partial Content
                            logger.info(f"Resuming download from byte position {existing_size}")
                        else:
                            # Server doesn't support range requests, start over
                            logger.warning("Server doesn't support resume, starting from beginning")
                            existing_size = 0
                            mode = "wb"
                            # Close this response and make a new request
                            response.close()
                            with self.client.stream("GET", download_url) as new_response:
                                return self._handle_download_response(
                                    new_response, output_path, mode, existing_size, 
                                    file_size, progress_bar, verify_size, resume, download_url)
                    
                    # Continue with normal download for this response
                    success = self._handle_download_response(
                        response, output_path, mode, existing_size, 
                        file_size, progress_bar, verify_size, resume, download_url)
                        
                    if success:
                        return True
                    
                    # If download failed but we're using mirrors, try another mirror
                    if self.mirrors_enabled and self.mirror_manager:
                        parsed_url = httpx.URL(download_url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.host}"
                        self.mirror_manager.report_failure(base_url)
                        
                        # Get a new mirror URL for the next attempt
                        if book_id > 0:
                            download_url = self._get_download_url(book_id, url)
                            logger.info(f"Retrying with new mirror: {download_url}")
                            retry_count += 1
                            # Wait a bit before retrying
                            time.sleep(1)
                            continue
            
            except Exception as e:
                # Log specific error types differently but handle them the same
                if isinstance(e, httpx.HTTPError):
                    logger.error(f"HTTP error downloading {download_url}: {e}")
                elif isinstance(e, OSError):
                    logger.error(f"IO error downloading {download_url}: {e}")
                else:
                    logger.error(f"Error downloading {download_url}: {e}")
                
                # Report failure to mirror manager and try another mirror if available
                if self.mirrors_enabled and self.mirror_manager and book_id > 0:
                    parsed_url = httpx.URL(download_url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.host}"
                    self.mirror_manager.report_failure(base_url)
                    
                    # Get a new mirror URL for the next attempt
                    download_url = self._get_download_url(book_id, url)
                    logger.info(f"Retrying with new mirror after error: {download_url}")
                    retry_count += 1
                    # Wait a bit before retrying
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                
                # If we're not using mirrors or can't find another mirror, fail
                if not resume and output_path.exists():
                    output_path.unlink()
                return False
            
            # If we reach here, increment retry count and try again if we haven't exhausted retries
            retry_count += 1
            
        # If we've exhausted all retries, return failure
        logger.error(f"Failed to download {url} after {max_retries} attempts with different mirrors")
        return False

    def download_multiple_epubs(
        self,
        downloads: list[tuple[str, Union[str, Path], Optional[int]]],
        delay: float = 1.0,
        continue_on_error: bool = True,
    ) -> dict[str, bool]:
        """Download multiple EPUB files with a delay between downloads.

        Args:
            downloads: List of (url, output_path, book_id) tuples. book_id is optional.
            delay: Delay in seconds between downloads.
            continue_on_error: Whether to continue if a download fails.

        Returns:
            Dictionary mapping URLs to success status.
        """
        results = {}

        for i, download_info in enumerate(downloads):
            # Handle both 2-tuple (url, path) and 3-tuple (url, path, book_id) formats
            if len(download_info) == 3:
                url, output_path, book_id = download_info
            else:
                url, output_path = download_info
                book_id = 0
                
            try:
                # Add delay between downloads (except for the first one)
                if i > 0 and delay > 0:
                    time.sleep(delay)

                success = self.download_epub(url, output_path, book_id=book_id)
                results[url] = success

                if not success and not continue_on_error:
                    break

            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                results[url] = False

                if not continue_on_error:
                    raise

        return results
        
    def find_incomplete_downloads(self, download_dir: Union[str, Path]) -> List[Path]:
        """Find potentially incomplete downloads in the given directory.
        
        This scans for files that might be partial downloads by comparing their size
        with typical EPUB file sizes. Files under 10KB are likely incomplete.
        
        Args:
            download_dir: Directory to scan for incomplete downloads.
            
        Returns:
            List of paths to potentially incomplete downloads.
        """
        download_dir = Path(download_dir)
        incomplete_files = []
        
        if not download_dir.exists() or not download_dir.is_dir():
            logger.warning(f"Download directory {download_dir} doesn't exist or is not a directory")
            return incomplete_files
            
        for file_path in download_dir.glob("*.epub"):
            try:
                # Check if file exists and is suspiciously small (likely incomplete)
                if file_path.exists() and file_path.stat().st_size < 10240:  # Less than 10KB
                    incomplete_files.append(file_path)
                    logger.info(f"Found potential incomplete download: {file_path}")
            except Exception as e:
                logger.error(f"Error checking file {file_path}: {e}")
                
        return incomplete_files
        
    def resume_incomplete_downloads(
        self,
        incomplete_files: List[Path],
        url_mapping: Dict[Path, str],
        progress_bar: bool = True,
    ) -> Dict[Path, bool]:
        """Resume downloading incomplete files with their respective URLs.
        
        Args:
            incomplete_files: List of paths to incomplete files.
            url_mapping: Dictionary mapping file paths to their download URLs.
            progress_bar: Whether to show progress bars during downloads.
            
        Returns:
            Dictionary mapping file paths to download success status.
        """
        results = {}
        
        for file_path in incomplete_files:
            if file_path not in url_mapping:
                logger.warning(f"No URL found for {file_path}, skipping resume")
                results[file_path] = False
                continue
                
            url = url_mapping[file_path]
            logger.info(f"Resuming download for {file_path} from {url}")
            
            try:
                # Extract book ID from URL if possible
                book_id = 0
                try:
                    # Try to extract from path like "12345.epub" or "pg12345.epub"
                    filename = Path(file_path).name
                    if filename.startswith("pg") and filename.endswith(".epub"):
                        book_id_str = filename[2:].split(".")[0]
                        if book_id_str.isdigit():
                            book_id = int(book_id_str)
                    elif filename.isdigit():
                        book_id = int(filename.split(".")[0])
                except (ValueError, IndexError):
                    book_id = 0
                
                success = self.download_epub(
                    url=url,
                    output_path=file_path,
                    progress_bar=progress_bar,
                    verify_size=True,
                    resume=True,
                    book_id=book_id
                )
                results[file_path] = success
            except Exception as e:
                logger.error(f"Error resuming download for {file_path}: {e}")
                results[file_path] = False
            
        return results

    def stream_download(
        self,
        url: str,
        output_stream: IO[bytes],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        book_id: int = 0,
    ) -> int:
        """Stream download an EPUB file to a file-like object.

        Args:
            url: URL of the EPUB file to download.
            output_stream: File-like object to write the content to.
            progress_callback: Optional callback function that receives
                              (downloaded_bytes, total_bytes) as arguments.
            book_id: Optional book ID for mirror selection.

        Returns:
            Total number of bytes downloaded.

        Raises:
            httpx.HTTPError: If there's an error during the HTTP request.
        """
        total_downloaded = 0
        
        # Get the download URL (possibly from a mirror)
        download_url = self._get_download_url(book_id, url)
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                with self.client.stream("GET", download_url) as response:
                    response.raise_for_status()

                    # Get total file size
                    total_size = int(response.headers.get("content-length", 0))

                    # Download and write chunks
                    for chunk in response.iter_bytes(chunk_size=self.chunk_size):
                        output_stream.write(chunk)
                        total_downloaded += len(chunk)

                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(total_downloaded, total_size)

                    logger.info(f"Stream downloaded {total_downloaded} bytes from {download_url}")
                    
                    # Report success to mirror manager if appropriate
                    if self.mirror_manager and self.mirrors_enabled:
                        parsed_url = httpx.URL(download_url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.host}"
                        self.mirror_manager.report_success(base_url)
                        
                    return total_downloaded

            except httpx.HTTPError as e:
                logger.error(f"HTTP error during stream download of {download_url}: {e}")
                
                # Report failure to mirror manager and try another mirror if available
                if self.mirrors_enabled and self.mirror_manager and book_id > 0:
                    parsed_url = httpx.URL(download_url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.host}"
                    self.mirror_manager.report_failure(base_url)
                    
                    # Get a new mirror URL for the next attempt
                    download_url = self._get_download_url(book_id, url)
                    logger.info(f"Retrying stream with new mirror: {download_url}")
                    retry_count += 1
                    # Reset stream position if possible
                    if hasattr(output_stream, 'seek') and hasattr(output_stream, 'truncate'):
                        output_stream.seek(0)
                        output_stream.truncate(0)
                        total_downloaded = 0
                    # Wait a bit before retrying
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                
                # If we're not using mirrors or can't find another mirror, re-raise
                raise
            
            # If we reach here, the download was successful
            break
            
        # If we've exhausted all retries, return the total bytes downloaded (might be 0)
        return total_downloaded