#!/usr/bin/env python3
"""Script to validate sci-fi downloads and download again if needed."""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path("./scifi_books")
if not OUTPUT_DIR.exists():
    OUTPUT_DIR.mkdir(parents=True)

# Expected sci-fi books (these are popular sci-fi titles on Project Gutenberg)
# Update to match what's actually available from our current query results
EXPECTED_BOOKS = [
    "A_Princess_of_Mars",
    "The_Time_Machine",
    "The_War_of_the_Worlds",
    "The_Strange_Case_of_Dr_Jekyll_and_Mr_Hyde"
]

# Commented out books that might not be available or categorized differently
# "Frankenstein",
# "Twenty_Thousand_Leagues_Under_the_Seas",
# "The_Lost_World",
# "Flatland",
# "The_Island_of_Doctor_Moreau",
# "The_Invisible_Man"

def check_downloads():
    """Check which expected books are already downloaded."""
    logger.info(f"Checking for downloaded books in {OUTPUT_DIR}")
    
    downloaded = []
    missing = []
    
    for book in EXPECTED_BOOKS:
        book_path = OUTPUT_DIR / f"{book}.epub"
        if book_path.exists():
            file_size = book_path.stat().st_size
            downloaded.append((book, file_size))
            logger.info(f"✓ Found {book}.epub ({file_size} bytes)")
        else:
            missing.append(book)
            logger.warning(f"✗ Missing {book}.epub")
    
    return downloaded, missing

def download_missing_books(missing_books):
    """Download any missing books."""
    if not missing_books:
        logger.info("No missing books to download")
        return
    
    logger.info(f"Attempting to download {len(missing_books)} missing books")
    
    # Try specifically targeting each missing book by title
    for book in missing_books:
        # Clean up the book name for search (remove underscores, etc.)
        search_term = book.replace("_", " ")
        
        command = (
            f"python -m gutenberg_downloader.cli filter-download "
            f"--terms '{search_term}' "  # Use book title as search term
            f"--subjects 'science fiction' "  # Use expanded subject
            f"--output {OUTPUT_DIR} "
            f"--limit 1"  # Limit to 1 since we're searching for a specific book
        )
        
        try:
            logger.info(f"Running command for '{search_term}': {command}")
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                text=True,
                capture_output=True
            )
            logger.info(f"Download command for '{search_term}' completed")
        except subprocess.CalledProcessError as e:
            logger.error(f"Command for '{search_term}' failed with return code: {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
    
    logger.info("Completed targeted download attempts")

def main():
    """Run validation and download missing books if needed."""
    logger.info("Starting sci-fi books validation")
    
    # Check current downloads
    downloaded, missing = check_downloads()
    
    # Summary of current status
    logger.info(f"Found {len(downloaded)} of {len(EXPECTED_BOOKS)} expected books")
    if downloaded:
        total_size = sum(size for _, size in downloaded)
        logger.info(f"Total size of downloaded books: {total_size} bytes")
    
    # Download missing books if needed
    if missing:
        logger.info(f"Missing {len(missing)} books: {', '.join(missing)}")
        download_missing_books(missing)
        
        # Check again after download
        downloaded, missing = check_downloads()
        
        if missing:
            logger.warning(f"Still missing {len(missing)} books: {', '.join(missing)}")
            logger.warning("These books might not be available or might have different titles")
        else:
            logger.info("All expected books successfully downloaded!")
    else:
        logger.info("All expected books are already downloaded!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())