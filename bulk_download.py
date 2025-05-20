#!/usr/bin/env python3
"""Bulk downloader script for Project Gutenberg books."""

import os
import sys
import logging
import time
from pathlib import Path

from gutenberg_downloader.smart_downloader import SmartDownloader
from gutenberg_downloader.logger import setup_logger

# Set up logging
logger = setup_logger(level=logging.INFO)

# Output directory
OUTPUT_DIR = Path("./bulk_downloads")
if not OUTPUT_DIR.exists():
    OUTPUT_DIR.mkdir(parents=True)

def download_popular_books(limit=300):
    """Download popular English books with EPUB format.
    
    Args:
        limit: Number of books to download
    """
    logger.info(f"Starting bulk download of {limit} popular English books")
    
    # Note about database content
    logger.warning("WARNING: The database seems to have only 7 books. To download 300 books, you need to:")
    logger.warning("1. Run discovery first to populate the database with more books")
    logger.warning("2. Use the api_discovery module to fetch more books from the Gutenberg API")
    logger.warning("3. Run catalog_importer to import the full Project Gutenberg catalog")
    
    # Initialize the smart downloader
    start_time = time.time()
    
    with SmartDownloader() as downloader:
        # Get popular English books with EPUB format
        logger.info("Fetching popular English books with EPUB format...")
        books = downloader.db.get_popular_english_epubs(limit=limit)
        
        if not books:
            logger.error("No books found in the database. Make sure to run discovery first.")
            return False
            
        logger.info(f"Found {len(books)} books to download")
        
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
            
            # Find EPUB URL from book data
            epub_url = None
            for format_type, url in book.get('formats', {}).items():
                if 'epub' in format_type.lower():
                    epub_url = url
                    break
            
            if not epub_url:
                logger.warning(f"No EPUB URL found for book {book_id}: {title}")
                # Try Project Gutenberg URL pattern as fallback
                epub_url = f"https://www.gutenberg.org/ebooks/{book_id}.epub"
            
            # Progress info
            logger.info(f"Downloading [{i}/{len(books)}] {book_id}: {title}")
            
            # Download the book
            success = downloader.download_book(
                book_id,
                epub_url, 
                OUTPUT_DIR,
                filename=filename
            )
            
            if success:
                success_count += 1
                logger.info(f"✓ Successfully downloaded to {filename}")
            else:
                failed_count += 1
                logger.error(f"✗ Failed to download book {book_id}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Print summary
    logger.info(f"\n{'=' * 50}")
    logger.info(f"Download Summary:")
    logger.info(f"Successfully downloaded: {success_count} books")
    if failed_count > 0:
        logger.info(f"Failed downloads: {failed_count} books")
    logger.info(f"Books saved to: {OUTPUT_DIR}")
    logger.info(f"Total time: {elapsed_time:.2f} seconds")
    logger.info(f"{'=' * 50}")
    
    return success_count > 0

def resume_pending_downloads():
    """Resume any pending or failed downloads."""
    logger.info("Checking for pending or failed downloads to resume...")
    
    with SmartDownloader() as downloader:
        success_count, failed_count = downloader.resume_all_downloads(OUTPUT_DIR)
        
        if success_count > 0:
            logger.info(f"Successfully resumed {success_count} downloads")
        
        if failed_count > 0:
            logger.warning(f"Failed to resume {failed_count} downloads")
            
        if success_count == 0 and failed_count == 0:
            logger.info("No pending downloads to resume")

def direct_download_top_books(limit=300):
    """Directly download popular books by ID.
    
    This function uses a known list of popular book IDs
    to download directly from Project Gutenberg, bypassing
    the need for format URLs in the database.
    
    Args:
        limit: Number of books to download
    """
    # List of popular book IDs (derived from Project Gutenberg popularity lists)
    popular_ids = [
        1342, 84, 1661, 2701, 11, 1952, 2554, 1080, 98, 2591, 174, 345, 46, 1400, 41, 16328, 2600, 1399, 158, 
        76, 1260, 55, 120, 74, 2500, 5200, 2814, 16, 161, 219, 10, 514, 1232, 844, 1497, 2148, 236, 208, 1250, 
        135, 2097, 203, 25344, 408, 42, 30254, 1184, 2680, 205, 19942, 45, 36, 75, 1513, 139, 35, 768, 730, 
        1727, 33283, 815, 6130, 62, 32, 105, 103, 863, 394, 345, 2542, 100, 786, 107, 5740, 1251, 23, 19337, 
        1404, 8800, 1023, 145, 600, 3600, 244, 829, 1064, 4300, 1998, 160, 34901, 22381, 209, 1228, 1934, 4363, 
        1112, 64317
    ]
    
    logger.info(f"Starting direct download of up to {limit} popular books")
    
    # Initialize the smart downloader
    start_time = time.time()
    
    with SmartDownloader() as downloader:
        # Limit to the requested number
        book_ids = popular_ids[:limit]
        
        # Download books
        success_count = 0
        failed_count = 0
        
        for i, book_id in enumerate(book_ids, 1):
            # Get book data if available
            book = downloader.db.get_book(book_id)
            
            # Get title from database or use placeholder
            if book:
                title = book.get('title', f'book_{book_id}')
            else:
                title = f"book_{book_id}"
            
            # Generate filename
            clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            clean_title = clean_title.replace(" ", "_")[:100]  # Limit length
            filename = f"{clean_title}.epub"
            
            # Create direct URL to EPUB
            epub_url = f"https://www.gutenberg.org/ebooks/{book_id}.epub"
            
            # Progress info
            logger.info(f"Downloading [{i}/{len(book_ids)}] {book_id}: {title}")
            
            # Download the book
            success = downloader.download_book(
                book_id,
                epub_url, 
                OUTPUT_DIR,
                filename=filename
            )
            
            if success:
                success_count += 1
                logger.info(f"✓ Successfully downloaded to {filename}")
            else:
                failed_count += 1
                logger.error(f"✗ Failed to download book {book_id}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Print summary
    logger.info(f"\n{'=' * 50}")
    logger.info(f"Download Summary:")
    logger.info(f"Successfully downloaded: {success_count} books")
    if failed_count > 0:
        logger.info(f"Failed downloads: {failed_count} books")
    logger.info(f"Books saved to: {OUTPUT_DIR}")
    logger.info(f"Total time: {elapsed_time:.2f} seconds")
    logger.info(f"{'=' * 50}")
    
    return success_count > 0

def main():
    """Run the bulk download script."""
    logger.info("Starting bulk download script")
    
    try:
        # Try the database-based download first
        db_result = download_popular_books(limit=300)
        
        # Always try direct download since we want 300 books total
        logger.info("Starting direct download to get more books")
        direct_download_top_books(limit=300)
        
        # Resume any failed downloads
        resume_pending_downloads()
        
        return 0
    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user. You can resume later.")
        return 0
    except Exception as e:
        logger.exception(f"Error during bulk download: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())