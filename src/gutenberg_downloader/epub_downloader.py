"""EPUB downloader module for downloading EPUB files from Project Gutenberg.

This module provides functionality to download EPUB files with proper error handling,
progress tracking, and file management.
"""

import logging
import time
from pathlib import Path
from typing import IO, Optional, Union

import httpx
from tqdm import tqdm

from .constants import DEFAULT_USER_AGENT, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class EpubDownloader:
    """Handles downloading of EPUB files from Project Gutenberg."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = REQUEST_TIMEOUT,
        chunk_size: int = 8192,
    ):
        """Initialize the EPUB downloader.

        Args:
            user_agent: User agent string for HTTP requests.
            timeout: Timeout in seconds for HTTP requests.
            chunk_size: Size of chunks to read/write during download.
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
        )

    def __enter__(self) -> "EpubDownloader":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and clean up resources."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def download_epub(
        self,
        url: str,
        output_path: Union[str, Path],
        progress_bar: bool = True,
        verify_size: bool = True,
    ) -> bool:
        """Download an EPUB file from the given URL.

        Args:
            url: URL of the EPUB file to download.
            output_path: Path where the EPUB file should be saved.
            progress_bar: Whether to show a progress bar during download.
            verify_size: Whether to verify the downloaded file size.

        Returns:
            True if download was successful, False otherwise.

        Raises:
            httpx.HTTPError: If there's an error during the HTTP request.
            IOError: If there's an error writing the file.
        """
        output_path = Path(output_path)

        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # First, get the file size with a HEAD request
            file_size = None
            if verify_size or progress_bar:
                try:
                    head_response = self.client.head(url)
                    head_response.raise_for_status()
                    file_size = int(head_response.headers.get("content-length", 0))
                except (httpx.HTTPError, ValueError):
                    logger.warning(f"Could not determine file size for {url}")

            # Download the file
            with self.client.stream("GET", url) as response:
                response.raise_for_status()

                # Get content length from GET response if not already obtained
                if file_size is None:
                    file_size = int(response.headers.get("content-length", 0))

                # Setup progress bar if requested
                progress = None
                if progress_bar and file_size > 0:
                    progress = tqdm(
                        total=file_size,
                        unit="B",
                        unit_scale=True,
                        desc=output_path.name,
                    )

                # Download and write the file
                downloaded_size = 0
                with open(output_path, "wb") as file:
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
                    output_path.unlink()  # Remove incomplete file
                    return False

                logger.info(f"Successfully downloaded {url} to {output_path}")
                return True

        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading {url}: {e}")
            # Clean up partial download
            if output_path.exists():
                output_path.unlink()
            raise
        except OSError as e:
            logger.error(f"IO error downloading {url}: {e}")
            # Clean up partial download
            if output_path.exists():
                output_path.unlink()
            raise

    def download_multiple_epubs(
        self,
        downloads: list[tuple[str, Union[str, Path]]],
        delay: float = 1.0,
        continue_on_error: bool = True,
    ) -> dict[str, bool]:
        """Download multiple EPUB files with a delay between downloads.

        Args:
            downloads: List of (url, output_path) tuples.
            delay: Delay in seconds between downloads.
            continue_on_error: Whether to continue if a download fails.

        Returns:
            Dictionary mapping URLs to success status.
        """
        results = {}

        for i, (url, output_path) in enumerate(downloads):
            try:
                # Add delay between downloads (except for the first one)
                if i > 0 and delay > 0:
                    time.sleep(delay)

                success = self.download_epub(url, output_path)
                results[url] = success

                if not success and not continue_on_error:
                    break

            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                results[url] = False

                if not continue_on_error:
                    raise

        return results

    def stream_download(
        self,
        url: str,
        output_stream: IO[bytes],
        progress_callback: Optional[callable] = None,
    ) -> int:
        """Stream download an EPUB file to a file-like object.

        Args:
            url: URL of the EPUB file to download.
            output_stream: File-like object to write the content to.
            progress_callback: Optional callback function that receives
                              (downloaded_bytes, total_bytes) as arguments.

        Returns:
            Total number of bytes downloaded.

        Raises:
            httpx.HTTPError: If there's an error during the HTTP request.
        """
        total_downloaded = 0

        try:
            with self.client.stream("GET", url) as response:
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

                logger.info(f"Stream downloaded {total_downloaded} bytes from {url}")
                return total_downloaded

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during stream download of {url}: {e}")
            raise
