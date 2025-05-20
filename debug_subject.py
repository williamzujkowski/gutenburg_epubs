#!/usr/bin/env python3
"""Debug subject search with 'scifi'."""

import logging
from pathlib import Path
from src.gutenberg_downloader.enhanced_downloader import EnhancedDownloader
from src.gutenberg_downloader.database import BookDatabase
from src.gutenberg_downloader.logger import setup_logger

# Setup detailed logging
setup_logger(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("Checking for 'scifi' as a subject in the database...")
db = BookDatabase(db_path="gutenberg_books.db")

# Check if 'scifi' exists as a subject
with db._get_connection() as conn:
    cursor = conn.cursor()
    
    print("\nSearching subjects table for 'scifi'...")
    cursor.execute("SELECT * FROM subjects WHERE name LIKE ?", ("%scifi%",))
    scifi_subjects = cursor.fetchall()
    print(f"Found {len(scifi_subjects)} subjects containing 'scifi'")
    for subj in scifi_subjects:
        print(f"- {subj['name']}")
        
    print("\nSearching for similar science fiction terms...")
    for term in ["science fiction", "sci-fi", "science-fiction", "sf"]:
        cursor.execute("SELECT COUNT(*) FROM subjects WHERE name LIKE ?", (f"%{term}%",))
        count = cursor.fetchone()[0]
        print(f"- '{term}': {count} matches")
        
    # Check for books with science fiction subjects
    print("\nChecking which subject terms are actually assigned to books...")
    cursor.execute("""
        SELECT s.name, COUNT(DISTINCT b.book_id) as book_count
        FROM subjects s
        JOIN book_subjects bs ON s.subject_id = bs.subject_id
        JOIN books b ON bs.book_id = b.book_id
        WHERE s.name LIKE '%science%fiction%' OR s.name LIKE '%sci%fi%'
        GROUP BY s.name
        ORDER BY book_count DESC
    """)
    subject_counts = cursor.fetchall()
    for row in subject_counts:
        print(f"- '{row[0]}': {row[1]} books")
        
print("\nTesting enhanced downloader with 'scifi' subject...")
with EnhancedDownloader(db_path="gutenberg_books.db") as downloader:
    print("\nUsing 'scifi':")
    books = downloader.search_books_by_filters(
        subjects=["scifi"],
        language="en",
        limit=10
    )
    print(f"Found {len(books)} books with subject 'scifi'")
    
    print("\nUsing 'science fiction':")
    books = downloader.search_books_by_filters(
        subjects=["science fiction"],
        language="en",
        limit=10
    )
    print(f"Found {len(books)} books with subject 'science fiction'")
    
    print("\nTrying a multi-term approach...")
    books = downloader.search_books_by_filters(
        subjects=["science fiction", "scifi", "sci-fi"],
        language="en",
        limit=10
    )
    print(f"Found {len(books)} books with combined subjects")
    for book in books:
        print(f"- {book.get('book_id')}: {book.get('title')}")