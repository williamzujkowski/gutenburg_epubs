#!/usr/bin/env python3
"""Script to import Project Gutenberg catalog from RDF files."""

import os
import sys
import logging
import time
from pathlib import Path

from gutenberg_downloader.catalog_importer import CatalogImporter
from gutenberg_downloader.logger import setup_logger

# Set up logging
logger = setup_logger(level=logging.INFO)

def import_catalog(rdf_files_path=None, limit=None):
    """Import Project Gutenberg catalog from RDF files.
    
    Args:
        rdf_files_path: Path to the RDF files directory
        limit: Maximum number of books to import
    """
    logger.info("Starting Gutenberg catalog import")
    
    # Create importer
    importer = CatalogImporter(
        db_path="gutenberg_books.db"
    )
    
    # Import catalog
    start_time = time.time()
    
    # Choose format to import (CSV is smaller and faster)
    format_type = "csv"  # or "rdf" for more complete metadata
    
    logger.info(f"Importing catalog using {format_type} format...")
    
    try:
        # The import_catalog method downloads the catalog automatically
        imported = importer.import_catalog(format=format_type)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Print summary
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Import Summary:")
        logger.info(f"Books successfully imported: {imported}")
        logger.info(f"Total time: {elapsed_time:.2f} seconds")
        if elapsed_time > 0 and imported > 0:
            rate = imported / elapsed_time
            logger.info(f"Processing rate: {rate:.1f} books/sec")
        logger.info(f"{'=' * 50}")
        
        return imported
        
    except Exception as e:
        logger.exception(f"Error importing catalog: {e}")
        return 0

def main():
    """Run the catalog import script."""
    logger.info("Starting catalog import process")
    
    try:
        # Import catalog
        imported = import_catalog(limit=5000)  # Limit to 5000 books for initial test
        
        if imported > 0:
            logger.info(f"Catalog import complete. Imported {imported} books.")
            logger.info("You can now run bulk_download.py to download books")
        else:
            logger.warning("No books were imported. Check if catalog files are available.")
        
        return 0
    except KeyboardInterrupt:
        logger.info("\nImport interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Error during import: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())