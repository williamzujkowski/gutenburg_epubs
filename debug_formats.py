#!/usr/bin/env python3
"""Debug formats availability in the database."""

import logging
from pathlib import Path
from src.gutenberg_downloader.database import BookDatabase
from src.gutenberg_downloader.logger import setup_logger

# Setup logging
setup_logger(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Checking format information in database...")
db = BookDatabase(db_path="gutenberg_books.db")

# Check one of the found books
book_id = 35  # The Time Machine
book = db.get_book(book_id)

print(f"\nBook ID: {book_id}")
print(f"Title: {book.get('title')}")
print(f"Authors: {', '.join([a.get('name', 'Unknown') for a in book.get('authors', [])])}")
print("\nAvailable formats:")
formats = book.get('formats', {})
if formats:
    for format_type, url in formats.items():
        print(f"- {format_type}: {url}")
else:
    print("No formats available")

# Check format records directly
print("\nQuerying formats table directly:")
with db._get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM formats")
    count = cursor.fetchone()[0]
    print(f"Total format records: {count}")
    
    cursor.execute("SELECT DISTINCT format_type FROM formats")
    format_types = [row[0] for row in cursor.fetchall()]
    print(f"Format types in database: {format_types}")
    
    cursor.execute("SELECT COUNT(*) FROM formats WHERE format_type LIKE '%epub%'")
    epub_count = cursor.fetchone()[0]
    print(f"EPUB format records: {epub_count}")
    
    # Check if the science fiction books have any format records
    cursor.execute("""
        SELECT b.book_id, b.title, COUNT(f.format_id) as format_count
        FROM books b
        LEFT JOIN formats f ON b.book_id = f.book_id
        JOIN book_subjects bs ON b.book_id = bs.book_id
        JOIN subjects s ON bs.subject_id = s.subject_id
        WHERE s.name LIKE '%science fiction%'
        GROUP BY b.book_id
        LIMIT 10
    """)
    scifi_formats = cursor.fetchall()
    print("\nFormat records for science fiction books:")
    for row in scifi_formats:
        print(f"- Book {row[0]} ({row[1]}): {row[2]} format records")
        
# Check format availability with the API
print("\nChecking formats via API...")
from src.gutenberg_downloader.api_discovery import APIBookDiscovery

with APIBookDiscovery() as api:
    book_details = api.get_book_details(book_id)
    if book_details:
        print(f"\nAPI book details for book {book_id}:")
        print(f"Title: {book_details.get('metadata', {}).get('title')}")
        print("\nDownload links from API:")
        for format_type, url in book_details.get('download_links', {}).items():
            print(f"- {format_type}: {url}")
    else:
        print(f"No API details found for book {book_id}")