#!/usr/bin/env python3
"""Test the alias expansion in enhanced downloader."""

import logging
from pathlib import Path
from src.gutenberg_downloader.enhanced_downloader import EnhancedDownloader
from src.gutenberg_downloader.logger import setup_logger

# Setup logging
setup_logger(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Testing subject alias expansion...")

with EnhancedDownloader(db_path="gutenberg_books.db") as downloader:
    # Test aliases
    alias_tests = [
        "scifi",
        "sci-fi",
        "sf",
        "science fiction",
        "mystery",
        "detective"
    ]
    
    for alias in alias_tests:
        expanded = downloader.normalize_subjects(alias)
        print(f"Original: '{alias}' → Expanded: {expanded}")
    
    # Test actual search using alias
    print("\nSearching for books with 'scifi' alias...")
    books = downloader.search_books_by_filters(
        subjects=["scifi"],
        language="en",
        limit=5
    )
    print(f"Found {len(books)} books matching 'scifi' alias")
    
    for book in books:
        print(f"- {book.get('book_id')}: {book.get('title')}")
        
    # Test with alternate name
    print("\nTesting with command format...")
    output_dir = Path("./alias_test")
    output_dir.mkdir(exist_ok=True)
    
    # Check the SQL queries directly
    print("\nDebug SQL queries for subject expansion:")
    normalized = downloader.normalize_subjects("scifi")
    print(f"Normalized subjects: {normalized}")
    
    # Try direct SQL query 
    with downloader.db._get_connection() as conn:
        cursor = conn.cursor()
        
        # Use same query logic as in the function
        like_conditions = []
        params = []
        
        for subject in normalized:
            like_conditions.append("s.name LIKE ?")
            params.append(f"%{subject}%")
        
        query = f"""
            SELECT DISTINCT b.book_id, b.title FROM books b
            JOIN book_subjects bs ON b.book_id = bs.book_id
            JOIN subjects s ON bs.subject_id = s.subject_id
            WHERE ({' OR '.join(like_conditions)})
            AND b.language = ?
            ORDER BY b.download_count DESC
            LIMIT 5
        """
        
        params.append("en")
        print(f"SQL Query: {query}")
        print(f"Params: {params}")
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        print(f"Direct SQL results: {len(results)} books")
        for row in results:
            print(f"- {row[0]}: {row[1]}")
    
    print("\nRunning search_and_download:")
    
    # Enable debug logging for search_and_download
    logging.getLogger('src.gutenberg_downloader.enhanced_downloader').setLevel(logging.DEBUG)
    
    # Try with the string directly 
    success_count, failed_count = downloader.search_and_download(
        subjects="scifi",  # Test with string instead of list
        language="en",
        limit=1,
        output_dir=output_dir,
        skip_existing=True
    )
    
    print(f"Downloaded {success_count} sci-fi books, {failed_count} failed")