#!/usr/bin/env python3
"""Test script to verify mirror rotation during multiple downloads."""

import asyncio
import logging
import os
from pathlib import Path
from src.gutenberg_downloader.enhanced_downloader import EnhancedDownloader
from src.gutenberg_downloader.logger import setup_logger

# Setup logging
setup_logger(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
output_dir = Path("./test_mirror_rotation")
output_dir.mkdir(parents=True, exist_ok=True)

# Test book IDs (classics that are guaranteed to be available)
TEST_BOOKS = [
    (1342, "Pride and Prejudice by Jane Austen"),
    (84, "Frankenstein by Mary Shelley"),
    (2701, "Moby Dick by Herman Melville"),
    (46, "A Christmas Carol by Charles Dickens"),
    (1661, "The Adventures of Sherlock Holmes by Arthur Conan Doyle"),
]

async def main():
    """Run the mirror rotation test."""
    print("\n📚 Testing Mirror Rotation")
    print(f"📂 Output directory: {output_dir}")
    print("─" * 70)
    
    # Initialize enhanced downloader with mirror support
    with EnhancedDownloader(db_path="gutenberg_books.db", mirrors_enabled=True) as downloader:
        print(f"🔄 Mirror Sites: Enabled")
        print(f"📊 Books to download: {len(TEST_BOOKS)}")
        print("─" * 70)
        
        # Clean output directory first if not empty 
        if any(os.listdir(output_dir)):
            print("🧹 Cleaning output directory...")
            for file in output_dir.glob("*.epub"):
                try:
                    file.unlink()
                    print(f"🗑️  Deleted {file.name}")
                except Exception as e:
                    print(f"⚠️ Failed to delete {file.name}: {e}")
        
        # Download books
        mirrors_used = {}
        
        for book_id, description in TEST_BOOKS:
            print(f"\n📗 Downloading: {description} (ID: {book_id})")
            
            # Note: using downloader.download_book instead of search_and_download for simplicity
            book_url = downloader.mirror_manager.get_book_url(book_id)
            mirror_url = book_url.split("/ebooks/")[0] if "/ebooks/" in book_url else book_url.split(f"/{book_id}")[0]
            
            print(f"🔄 Selected mirror: {mirror_url}")
            
            # Track mirrors used
            mirrors_used[mirror_url] = mirrors_used.get(mirror_url, 0) + 1
            
            # Generate filename
            filename = description.split(" by ")[0].replace(" ", "_") + ".epub"
            
            # Download the book
            success = downloader.download_book(
                book_id,
                book_url,
                output_dir,
                filename=filename
            )
            
            if success:
                print(f"✅ Successfully downloaded to {output_dir / filename}")
            else:
                print(f"❌ Failed to download book {book_id}")
        
        # Print mirror usage summary
        print("\n📊 Mirror Usage Summary:")
        print("─" * 70)
        
        for mirror_url, count in mirrors_used.items():
            # Find the mirror name if possible
            mirror_name = "Unknown"
            for mirror in downloader.mirror_manager.mirrors:
                if mirror.base_url in mirror_url or mirror_url in mirror.base_url:
                    mirror_name = mirror.name
                    break
                    
            print(f"{mirror_name} ({mirror_url}): {count} books")
        
        print("─" * 70)
        print(f"Total unique mirrors used: {len(mirrors_used)}")
        
if __name__ == "__main__":
    asyncio.run(main())