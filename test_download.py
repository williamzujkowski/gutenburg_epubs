#!/usr/bin/env python3
"""Simple test script for downloading a book."""

from pathlib import Path
from src.gutenberg_downloader.epub_downloader import EpubDownloader

# Create download directory
output_dir = Path("./test_downloads")
output_dir.mkdir(parents=True, exist_ok=True)

# Initialize downloader with mirrors enabled
downloader = EpubDownloader(mirrors_enabled=True)

# Download Pride and Prejudice (book ID 1342)
url = "https://www.gutenberg.org/ebooks/1342.epub"
output_path = output_dir / "Pride_and_Prejudice.epub"
book_id = 1342

print(f"Downloading {url} to {output_path}")
success = downloader.download_epub(
    url=url,
    output_path=output_path,
    progress_bar=True,
    resume=True,
    book_id=book_id
)

if success:
    print(f"Successfully downloaded to {output_path}")
else:
    print(f"Failed to download the book")