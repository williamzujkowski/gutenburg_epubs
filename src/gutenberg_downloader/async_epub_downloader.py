"""Asynchronous EPUB downloader module with concurrent download capabilities.

This module provides async functionality for downloading EPUB files from Project Gutenberg
with support for concurrent downloads, progress reporting, and resumable downloads.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union, Tuple

import aiofiles
import httpx
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential
from tqdm.asyncio import tqdm

from .constants import (
    DEFAULT_USER_AGENT,
    MAX_DOWNLOAD_RETRIES,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


class AsyncEpubDownloader:
    """Asynchronously downloads EPUB files from Project Gutenberg with concurrent capabilities."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        max_retries: int = MAX_DOWNLOAD_RETRIES,
        timeout: float = REQUEST_TIMEOUT,
        max_concurrency: int = 5,
    ):
        """Initialize the async EPUB downloader.

        Args:
            user_agent: User agent string for HTTP requests.
            max_retries: Maximum number of download retry attempts.
            timeout: Request timeout in seconds.
            max_concurrency: Maximum number of concurrent downloads.
        """
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_concurrency = max_concurrency

        # Create client with custom headers
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def __aenter__(self) -> "AsyncEpubDownloader":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager and clean up resources."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def download_epub(
        self,
        url: str,
        output_path: Union[str, Path],
        progress_bar: bool = True,
        verify_size: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Download a single EPUB file asynchronously.

        Args:
            url: URL of the EPUB file to download.
            output_path: Path where the EPUB file will be saved.
            progress_bar: Whether to show a progress bar during download.
            verify_size: Whether to verify file size after download.
            progress_callback: Optional callback for custom progress reporting.

        Returns:
            True if download was successful, False otherwise.
        """
        async with self._semaphore:  # Control concurrency
            try:
                output_path = Path(output_path)
                # Create parent directory if it doesn't exist
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Use Tenacity for retry logic
                retry_strategy = AsyncRetrying(
                    stop=stop_after_attempt(self.max_retries),
                    wait=wait_exponential(multiplier=1, min=4, max=10),
                )

                async for attempt in retry_strategy:
                    with attempt:
                        # Stream download with progress tracking
                        success = await self._stream_download(
                            url,
                            output_path,
                            progress_bar=progress_bar,
                            progress_callback=progress_callback,
                        )

                        if success and verify_size:
                            # Verify file size
                            file_size = output_path.stat().st_size
                            logger.info(f"Downloaded {file_size:,} bytes to {output_path}")

                        return success

            except RetryError:
                logger.error(f"Failed to download {url} after {self.max_retries} attempts")
                return False
            except Exception as e:
                logger.error(f"Error downloading EPUB from {url}: {e}")
                return False
        
        # This should never be reached due to the retry logic
        return False

    async def _stream_download(
        self,
        url: str,
        output_path: Path,
        progress_bar: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Stream download with progress tracking and resume capability.

        Args:
            url: URL to download from.
            output_path: Path to save the file.
            progress_bar: Whether to show a progress bar.
            progress_callback: Optional callback for progress updates.

        Returns:
            True if download was successful, False otherwise.
        """
        # Check if file exists and we can resume
        existing_size = 0
        mode = "wb"
        
        if output_path.exists():
            existing_size = output_path.stat().st_size
            if existing_size > 0:
                logger.info(f"Found existing file {output_path.name} with {existing_size} bytes. Attempting resume.")
                mode = "ab"  # Append mode for resume

        try:
            # Set up headers for resume if needed
            headers = {}
            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"
                
            async with self.client.stream("GET", url, headers=headers) as response:
                # Check if server supports resume
                if existing_size > 0:
                    if response.status_code == 206:  # Partial Content
                        logger.info(f"Resuming download from byte position {existing_size}")
                    else:
                        # Server doesn't support range requests, start over
                        logger.warning("Server doesn't support resume, starting from beginning")
                        existing_size = 0
                        mode = "wb"
                        # Make a new request without range header
                        response = await self.client.stream("GET", url)
                
                response.raise_for_status()

                # Get content length for progress tracking
                if response.status_code == 206:  # Partial content
                    total_size = existing_size + int(response.headers.get("content-length", 0))
                else:
                    total_size = int(response.headers.get("content-length", 0))

                # Set up progress bar if requested
                pbar = None
                if progress_bar and total_size > 0:
                    pbar = tqdm(
                        total=total_size,
                        initial=existing_size,  # Start from existing size
                        unit="B",
                        unit_scale=True,
                        desc=output_path.name,
                    )

                # Write content to file
                async with aiofiles.open(output_path, mode) as file:
                    downloaded = existing_size
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        await file.write(chunk)
                        downloaded += len(chunk)

                        # Update progress
                        if pbar:
                            pbar.update(len(chunk))
                        if progress_callback:
                            progress_callback(downloaded, total_size)

                if pbar:
                    pbar.close()

                # Verify download
                if total_size > 0 and downloaded != total_size:
                    logger.warning(
                        f"Downloaded size mismatch: expected {total_size}, got {downloaded}"
                    )
                    # Don't delete the partial file - it can be resumed
                    return False

                return True

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading {url}: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error streaming download from {url}: {e}")
            return False

    async def download_multiple_epubs(
        self,
        downloads: list[tuple[str, Union[str, Path]]],
        progress_bar: bool = True,
        stop_on_error: bool = False,
        overall_progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict[str, bool]:
        """Download multiple EPUB files concurrently.

        Args:
            downloads: List of (url, output_path) tuples.
            progress_bar: Whether to show progress bars.
            stop_on_error: Whether to stop all downloads if one fails.
            overall_progress_callback: Callback for overall progress.

        Returns:
            Dictionary mapping URLs to download success status.
        """
        results = {}

        # Create overall progress bar
        overall_pbar = None
        if progress_bar:
            overall_pbar = tqdm(
                total=len(downloads),
                desc="Overall Progress",
                unit="files"
            )

        # Create tasks for concurrent downloads
        tasks = []
        for i, (url, output_path) in enumerate(downloads):
            task = self._download_with_progress(
                url,
                output_path,
                progress_bar=progress_bar,
                task_index=i,
                total_tasks=len(downloads),
                overall_pbar=overall_pbar,
                overall_progress_callback=overall_progress_callback,
            )
            tasks.append(task)

        # Execute downloads concurrently
        if stop_on_error:
            # Use gather with return_exceptions=False to stop on first error
            try:
                download_results = await asyncio.gather(*tasks, return_exceptions=False)
                for (url, _), success in zip(downloads, download_results):
                    results[url] = success
            except Exception as e:
                logger.error(f"Error during concurrent downloads: {e}")
                # Mark remaining downloads as failed
                for url, _ in downloads:
                    if url not in results:
                        results[url] = False
        else:
            # Continue on errors
            download_results_with_errors: list[Union[bool, BaseException]] = await asyncio.gather(*tasks, return_exceptions=True)
            for (url, _), result in zip(downloads, download_results_with_errors):
                if isinstance(result, Exception):
                    logger.error(f"Error downloading {url}: {result}")
                    results[url] = False
                else:
                    results[url] = bool(result)

        if overall_pbar:
            overall_pbar.close()

        # Log summary
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Downloaded {successful}/{len(downloads)} files successfully")

        return results

    async def _download_with_progress(
        self,
        url: str,
        output_path: Union[str, Path],
        progress_bar: bool,
        task_index: int,
        total_tasks: int,
        overall_pbar: Optional[tqdm] = None,
        overall_progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Download a single file with progress tracking.

        Args:
            url: URL to download.
            output_path: Output path for the file.
            progress_bar: Whether to show progress bars.
            task_index: Index of this task in the overall batch.
            total_tasks: Total number of tasks in the batch.
            overall_pbar: Overall progress bar instance.
            overall_progress_callback: Callback for overall progress.

        Returns:
            True if successful, False otherwise.
        """
        success = await self.download_epub(
            url,
            output_path,
            progress_bar=progress_bar,
            verify_size=True,
        )

        # Update overall progress
        if overall_pbar:
            overall_pbar.update(1)

        if overall_progress_callback:
            completed = task_index + 1
            overall_progress_callback(completed, total_tasks)

        return success
        
    async def find_incomplete_downloads(self, download_dir: Union[str, Path]) -> list[Path]:
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
        
    async def resume_incomplete_downloads(
        self,
        incomplete_files: list[Path],
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
            
            success = await self.download_epub(
                url=url,
                output_path=file_path,
                progress_bar=progress_bar,
                verify_size=True
            )
            
            results[file_path] = success
            
        return results
