#!/usr/bin/env python3
"""Debug script to test search functionality."""

import logging
from pathlib import Path
from src.gutenberg_downloader.database import BookDatabase 
from src.gutenberg_downloader.enhanced_downloader import EnhancedDownloader
from src.gutenberg_downloader.logger import setup_logger

# Setup logging
setup_logger(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Checking database...")
# Try regular database search first
db = BookDatabase(db_path="gutenberg_books.db")
stats = db.get_statistics()

print(f"Total books in database: {stats.get('total_books', 0):,}")
print(f"Total authors: {stats.get('total_authors', 0):,}")
print(f"Total subjects: {stats.get('total_subjects', 0):,}")
print(f"Books with EPUB: {stats.get('books_with_epub', 0):,}")

print("\nTesting subject search...")
# Test direct database search with more debug info
print("SQL debug enabled for database.py")
logging.getLogger('src.gutenberg_downloader.database').setLevel(logging.DEBUG)

books = db.search_books(
    subject="science fiction",
    language="en",
    limit=5
)
print(f"Found {len(books)} books with subject 'science fiction'")

for book in books:
    print(f"- {book.get('book_id')}: {book.get('title')}")

print("\nTesting enhanced downloader search...")
# Test enhanced downloader search with debug info
print("SQL debug enabled for enhanced_downloader.py")
logging.getLogger('src.gutenberg_downloader.enhanced_downloader').setLevel(logging.DEBUG)

with EnhancedDownloader(db_path="gutenberg_books.db") as downloader:
    print("Direct subjects query to check structure...")
    with downloader.db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT name FROM subjects WHERE name LIKE ?", ("%science fiction%",))
        subject_rows = cursor.fetchall()
        print(f"Found {len(subject_rows)} subjects containing 'science fiction'")
        for row in subject_rows:
            print(f"- {row['name']}")
    
    books = downloader.search_books_by_filters(
        subjects=["science fiction"],
        language="en",
        limit=5
    )
    print(f"Enhanced search found {len(books)} books")
    
    for book in books:
        print(f"- {book.get('book_id')}: {book.get('title')}")
        
    # Try with a broader search term
    print("\nTrying broader search term 'fiction'...")
    books = downloader.search_books_by_filters(
        subjects=["fiction"],
        language="en",
        limit=5
    )
    print(f"Enhanced search found {len(books)} books with subject 'fiction'")
    
    for book in books:
        print(f"- {book.get('book_id')}: {book.get('title')}")