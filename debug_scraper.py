#!/usr/bin/env python3
"""Debug script to check the popular books page structure."""

from gutenberg_downloader.scraper import GutenbergScraper

def main():
    """Test the scraper."""
    with GutenbergScraper() as scraper:
        print("Testing popular books page...")
        books = scraper.get_popular_books(limit=5)
        
        if not books:
            print("No books found!")
        else:
            print(f"Found {len(books)} books:\n")
            for i, book in enumerate(books, 1):
                print(f"Book {i}:")
                for key, value in book.items():
                    print(f"  {key}: {value}")
                print()

if __name__ == "__main__":
    main()