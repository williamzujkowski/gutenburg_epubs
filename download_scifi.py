#!/usr/bin/env python3
"""Standalone script to download science fiction books."""

import logging
from pathlib import Path
from src.gutenberg_downloader.enhanced_downloader import EnhancedDownloader
from src.gutenberg_downloader.logger import setup_logger

# Setup logging
setup_logger(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
output_dir = Path("./scifi_books")
output_dir.mkdir(parents=True, exist_ok=True)

print("\n📚 Downloading Science Fiction Books")
print(f"📂 Output directory: {output_dir}")
print("─" * 50)

# Initialize enhanced downloader
with EnhancedDownloader(db_path="gutenberg_books.db") as downloader:
    # Download science fiction books
    subjects = ["science fiction"]
    language = "en"
    limit = 5
    
    print(f"🏷️  Subjects: {', '.join(subjects)}")
    print(f"🌐 Language: {language}")
    print(f"📊 Limit: {limit}")
    print("─" * 50)
    
    success_count, failed_count = downloader.search_and_download(
        subjects=subjects,
        language=language,
        limit=limit,
        output_dir=output_dir,
        skip_existing=True
    )
    
    # Print summary
    print("─" * 50)
    print(f"✅ Successfully downloaded: {success_count}")
    if failed_count > 0:
        print(f"❌ Failed downloads: {failed_count}")
    print(f"📂 Books saved to: {output_dir}")