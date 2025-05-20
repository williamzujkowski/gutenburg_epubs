#!/usr/bin/env python3
"""Discovery script to populate the database before bulk downloading."""

import os
import sys
import logging
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from gutenberg_downloader.api_discovery import APIBookDiscovery
from gutenberg_downloader.database import BookDatabase
from gutenberg_downloader.logger import setup_logger

# Set up logging
logger = setup_logger(level=logging.INFO)

def discover_books(start_id=1, end_id=1000, workers=10):
    """Discover books using the API and populate the database.
    
    Args:
        start_id: Starting book ID
        end_id: Ending book ID
        workers: Number of worker threads
    """
    logger.info(f"Starting book discovery from ID {start_id} to {end_id}")
    
    # Initialize database
    db = BookDatabase()
    
    # Get list of IDs to process
    book_ids = list(range(start_id, end_id + 1))
    total_books = len(book_ids)
    
    logger.info(f"Total books to process: {total_books}")
    
    # Track progress
    discovered = 0
    skipped = 0
    failed = 0
    
    start_time = time.time()
    
    # Process books in batches using ThreadPoolExecutor
    with APIBookDiscovery() as api:
        # Define worker function
        def process_book(book_id):
            try:
                # Check if book already exists in database
                existing = db.get_book(book_id)
                if existing:
                    return "skipped", book_id
                
                # Get book details from API
                book_data = api.get_book_by_id(book_id)
                
                if not book_data:
                    return "not_found", book_id
                
                # Check if book is in English
                languages = book_data.get("languages", [])
                if "en" not in languages:
                    return "not_english", book_id
                
                # Insert book into database
                success = db.insert_book(book_data)
                
                if success:
                    return "success", book_id
                else:
                    return "failed", book_id
                    
            except Exception as e:
                logger.error(f"Error processing book {book_id}: {e}")
                return "error", book_id
        
        # Process books using thread pool
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_id = {executor.submit(process_book, book_id): book_id for book_id in book_ids}
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_id), 1):
                book_id = future_to_id[future]
                try:
                    status, _ = future.result()
                    
                    if status == "success":
                        discovered += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        failed += 1
                        
                    # Log progress periodically
                    if i % 50 == 0 or i == total_books:
                        elapsed = time.time() - start_time
                        rate = i / elapsed if elapsed > 0 else 0
                        logger.info(f"Progress: {i}/{total_books} books processed ({rate:.1f} books/sec)")
                        logger.info(f"Status: {discovered} discovered, {skipped} skipped, {failed} failed")
                        
                except Exception as e:
                    logger.error(f"Error getting result for book {book_id}: {e}")
                    failed += 1
    
    # Log final summary
    elapsed_time = time.time() - start_time
    logger.info(f"\n{'=' * 50}")
    logger.info(f"Discovery Summary:")
    logger.info(f"Total books processed: {total_books}")
    logger.info(f"New books discovered: {discovered}")
    logger.info(f"Books already in database: {skipped}")
    logger.info(f"Failed or not found: {failed}")
    logger.info(f"Total time: {elapsed_time:.2f} seconds")
    if elapsed_time > 0:
        logger.info(f"Processing rate: {total_books / elapsed_time:.1f} books/sec")
    logger.info(f"{'=' * 50}")
    
    return discovered

def main():
    """Run the discovery script."""
    logger.info("Starting discovery script")
    
    try:
        # Process books in batches to avoid memory issues
        batch_size = 1000
        total_discovered = 0
        
        # Process first 10,000 books (should be enough to get many popular ones)
        for start_id in range(1, 10001, batch_size):
            end_id = min(start_id + batch_size - 1, 10000)
            discovered = discover_books(start_id, end_id)
            total_discovered += discovered
            
            # Log batch completion
            logger.info(f"Completed batch {start_id}-{end_id}, discovered {discovered} new books")
            
            # Break if we've discovered enough books
            if total_discovered >= 500:
                logger.info(f"Discovered {total_discovered} books, which should be enough for bulk download")
                break
        
        logger.info(f"Discovery complete. Total new books discovered: {total_discovered}")
        logger.info("You can now run bulk_download.py to download books")
        
        return 0
    except KeyboardInterrupt:
        logger.info("\nDiscovery interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Error during discovery: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())