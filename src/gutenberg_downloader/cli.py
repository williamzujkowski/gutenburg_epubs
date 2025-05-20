#!/usr/bin/env python3
"""Command-line interface for the Gutenberg EPUB downloader.

This module provides CLI functionality for discovering and downloading English ebooks
with EPUB format from Project Gutenberg with comprehensive filtering, database integration,
and mirror site support.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import __version__
from .api_discovery import APIBookDiscovery
from .async_api_discovery import AsyncAPIBookDiscovery
from .async_discovery import AsyncBookDiscovery
from .discovery import BookDiscovery
from .logger import setup_logger
from .api_discovery_db import APIBookDiscoveryDB
from .database import BookDatabase
from .enhanced_downloader import EnhancedDownloader
from .mirror_manager import MirrorManager

logger = logging.getLogger(__name__)


def create_main_parser() -> argparse.ArgumentParser:
    """Create parser for the main CLI.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="gutenberg-downloader",
        description="Project Gutenberg EPUB Downloader - A tool for discovering and downloading ebooks with optimal defaults for speed and reliability",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Default optimizations enabled:
  - Database usage (faster searches and resumable downloads)
  - Mirror site rotation (avoids rate limits, faster downloads)
  - Asynchronous mode (parallel downloads for better performance)
  - Resume capability (can continue interrupted downloads)
  - Skip existing files (won't re-download books you already have)

Use the --no-* flags to disable any of these features if needed.
        """
    )
    
    # Version info
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"gutenberg-downloader {__version__}"
    )
    
    # Global options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-error output"
    )
    
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Disable database usage (database is used by default)"
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default="gutenberg_books.db",
        help="Path to database file"
    )
    
    parser.add_argument(
        "--no-mirrors",
        action="store_true",
        help="Disable mirror site rotation (enabled by default)"
    )
    
    parser.add_argument(
        "--preferred-mirrors",
        type=str,
        help="Comma-separated list of preferred mirror URLs"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands",
        help="Command to execute"
    )
    
    # Discover command
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover popular books with EPUB format"
    )
    discover_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of books to display"
    )
    discover_parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Filter by language code"
    )
    discover_parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Save results to JSON file"
    )
    discover_parser.add_argument(
        "--sync-mode",
        action="store_true",
        help="Use synchronous mode for discovery (async mode is default)"
    )
    
    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search for books by title, author, or subject"
    )
    search_parser.add_argument(
        "--title",
        type=str,
        help="Search by title"
    )
    search_parser.add_argument(
        "--author",
        type=str,
        help="Search by author"
    )
    search_parser.add_argument(
        "--subject",
        type=str,
        help="Search by subject"
    )
    search_parser.add_argument(
        "--full-text",
        type=str,
        help="Full-text search (requires --use-db)"
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to display"
    )
    search_parser.add_argument(
        "--sync-mode",
        action="store_true",
        help="Use synchronous mode for search (async mode is default)"
    )
    search_parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Save results to JSON file"
    )
    
    # Download command
    download_parser = subparsers.add_parser(
        "download",
        help="Download a book by ID"
    )
    download_parser.add_argument(
        "book_id",
        type=int,
        help="Book ID to download"
    )
    download_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("downloads"),
        help="Output directory for downloaded book"
    )
    download_parser.add_argument(
        "--sync-mode",
        action="store_true",
        help="Use synchronous mode for download (async mode is default)"
    )
    
    # Download popular command
    download_popular_parser = subparsers.add_parser(
        "download-popular",
        help="Download popular books",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download 10 popular books with all optimizations enabled
  gutenberg-downloader download-popular --output ./popular/
  
  # Download 20 popular books with higher concurrency
  gutenberg-downloader download-popular --limit 20 --concurrency 8 --output ./popular/
  
  # Download using synchronous mode (slower but uses less resources)
  gutenberg-downloader download-popular --sync-mode --output ./popular/
  
  # Download with specific language filter
  gutenberg-downloader download-popular --language fr --output ./french_books/
"""
    )
    download_popular_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of books to download"
    )
    download_popular_parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Filter by language code"
    )
    download_popular_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("downloads"),
        help="Output directory for downloaded books"
    )
    download_popular_parser.add_argument(
        "--sync-mode",
        action="store_true",
        help="Use synchronous mode for downloads (async mode is default)"
    )
    download_popular_parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Maximum concurrent downloads (async mode only)"
    )
    
    # Database commands
    db_parser = subparsers.add_parser(
        "db",
        help="Database operations"
    )
    db_subparsers = db_parser.add_subparsers(
        dest="db_command",
        title="db_commands",
        description="Available database commands",
        help="Database command to execute"
    )
    
    # DB stats command
    db_stats_parser = db_subparsers.add_parser(
        "stats",
        help="Show database statistics"
    )
    
    # DB clear command
    db_clear_parser = db_subparsers.add_parser(
        "clear",
        help="Clear the database"
    )
    db_clear_parser.add_argument(
        "--force",
        action="store_true",
        help="Force clear without confirmation"
    )
    
    # Mirror commands
    mirror_parser = subparsers.add_parser(
        "mirrors",
        help="Mirror site operations"
    )
    mirror_subparsers = mirror_parser.add_subparsers(
        dest="mirror_command",
        title="mirror_commands",
        description="Available mirror commands",
        help="Mirror command to execute"
    )
    
    # Mirror status command
    mirror_status_parser = mirror_subparsers.add_parser(
        "status",
        help="Show mirror site status"
    )
    mirror_status_parser.add_argument(
        "--check-health",
        action="store_true",
        help="Force health check on all mirrors"
    )
    
    # Mirror update command
    mirror_update_parser = mirror_subparsers.add_parser(
        "update",
        help="Update mirror list from Project Gutenberg"
    )
    
    # Filter download command
    filter_download_parser = subparsers.add_parser(
        "filter-download",
        help="Download books with advanced filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download science fiction books (with all optimizations enabled by default)
  gutenberg-downloader filter-download --subjects "science fiction" --output ./scifi_books/
  
  # Download books matching multiple terms
  gutenberg-downloader filter-download --terms "space, aliens, future" --match-any --output ./space_books/
  
  # Download books with specific subjects and search terms
  gutenberg-downloader filter-download --subjects "adventure, pirates" --terms "treasure" --output ./pirate_books/
  
  # Filter by language and minimum downloads, and disable mirror rotation
  gutenberg-downloader --no-mirrors filter-download --subjects "philosophy" --language fr --min-downloads 100 --output ./philosophy/
  
  # Download without skipping existing files (to replace them)
  gutenberg-downloader filter-download --subjects "science fiction" --no-skip-existing --output ./scifi_books/
  
  # Force download even if files exist (useful for testing mirror fallback)
  gutenberg-downloader filter-download --subjects "science fiction" --force-download --output ./scifi/
"""
    )
    filter_download_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("downloads"),
        help="Output directory for downloaded books"
    )
    filter_download_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of books to download"
    )
    filter_download_parser.add_argument(
        "--terms",
        type=str,
        help="Search terms (comma-separated or quoted strings)"
    )
    filter_download_parser.add_argument(
        "--subjects",
        type=str,
        help="Filter by subjects/genres (comma-separated or quoted strings)"
    )
    filter_download_parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Filter by language code"
    )
    filter_download_parser.add_argument(
        "--min-downloads",
        type=int,
        help="Minimum download count"
    )
    filter_download_parser.add_argument(
        "--match-any",
        action="store_true",
        help="Match books with any of the search terms (default: must match all terms)"
    )
    filter_download_parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Don't skip books that already exist in the output directory"
    )
    
    filter_download_parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume capability for interrupted downloads"
    )
    
    filter_download_parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force download even if files already exist (for testing mirror fallback)"
    )
    
    # Resume download command
    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume interrupted downloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resume all interrupted downloads (with optimal defaults)
  gutenberg-downloader resume --output ./downloads/
  
  # Resume with synchronous mode (slower but uses fewer resources)
  gutenberg-downloader resume --sync-mode --output ./downloads/
  
  # Resume without using mirror sites
  gutenberg-downloader --no-mirrors resume --output ./downloads/
  
  # Show detailed progress when resuming
  gutenberg-downloader resume --output ./downloads/ --verbose
"""
    )
    resume_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("downloads"),
        help="Directory containing interrupted downloads"
    )
    resume_parser.add_argument(
        "--sync-mode",
        action="store_true",
        help="Use synchronous mode for resume (async mode is default)"
    )
    
    return parser


def discover_command(args: argparse.Namespace) -> int:
    """Execute the discover command to find popular books with EPUB format.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n📚 Discovering Popular Books")
        print("─" * 50)
        
        print(f"🔍 Finding up to {args.limit} popular books in language '{args.language}'...")
        
        if args.database_enabled:
            print(f"📊 Using database: {args.db_path}")
            from .api_discovery_db import APIBookDiscoveryDB
            discovery_service = APIBookDiscoveryDB(db_path=args.db_path)
        # Default to async mode unless explicitly requested otherwise
        elif not getattr(args, 'sync_mode', False):
            print("⚡ Using asynchronous discovery")
            if args.mirrors_enabled:
                print("🔄 Using mirror rotation for requests")
            
            from .async_api_discovery import AsyncAPIBookDiscovery
            discovery_service = AsyncAPIBookDiscovery()
        else:
            print("🔍 Using synchronous discovery")
            from .api_discovery import APIBookDiscovery
            discovery_service = APIBookDiscovery()
        
        with discovery_service:
            # Discover books
            # Use async mode by default unless sync_mode is specified
            async_mode = not getattr(args, 'sync_mode', False)
            if async_mode and hasattr(discovery_service, "discover_popular_english_epubs_async"):
                # Use asyncio to run the async method
                import asyncio
                books = asyncio.run(
                    discovery_service.discover_popular_english_epubs_async(limit=args.limit)
                )
            else:
                books = discovery_service.discover_popular_english_epubs(limit=args.limit)
            
            if not books:
                print("❌ No books found matching the criteria")
                return 1
                
            # Display results
            print(f"\n✅ Found {len(books)} books:")
            print("─" * 50)
            
            for i, book in enumerate(books, 1):
                title = book.get("title", "Unknown Title")
                author = book.get("metadata", {}).get("author", "Unknown Author")
                language = book.get("metadata", {}).get("language", "unknown")
                book_id = book.get("book_id", "N/A")
                
                print(f"{i}. [{book_id}] {title}")
                print(f"   Author: {author}")
                print(f"   Language: {language}")
                if "download_count" in book.get("metadata", {}):
                    print(f"   Downloads: {book['metadata']['download_count']}")
                print()
            
            # Save results to file if requested
            if args.output:
                import json
                args.output.parent.mkdir(parents=True, exist_ok=True)
                
                with open(args.output, "w") as f:
                    json.dump(books, f, indent=2)
                print(f"📄 Results saved to {args.output}")
            
            return 0
            
    except Exception as e:
        logger.error(f"Error in discover command: {e}")
        return 1


def search_command(args: argparse.Namespace) -> int:
    """Execute the search command with various criteria.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n🔍 Searching for Books")
        print("─" * 50)
        
        # Check search criteria
        if not any([args.title, args.author, args.subject, args.full_text]):
            print("❌ Error: You must specify at least one search criterion.")
            print("   Use --title, --author, --subject, or --full-text.")
            return 1
        
        # Print search criteria
        search_criteria = []
        if args.title:
            search_criteria.append(f"Title: '{args.title}'")
        if args.author:
            search_criteria.append(f"Author: '{args.author}'")
        if args.subject:
            search_criteria.append(f"Subject: '{args.subject}'")
        if args.full_text:
            search_criteria.append(f"Full text: '{args.full_text}'")
            
        print(f"🔎 Search criteria: {', '.join(search_criteria)}")
        print(f"📊 Max results: {args.limit}")
        
        # Setup appropriate discovery service
        if args.full_text and not args.database_enabled:
            print("⚠️ Full-text search requires database. Enabling database mode.")
            args.database_enabled = True
        
        if args.database_enabled:
            print(f"📊 Using database: {args.db_path}")
            from .database import BookDatabase
            db = BookDatabase(db_path=args.db_path)
            
            # Perform search based on criteria
            if args.full_text:
                print(f"🔍 Performing full-text search for '{args.full_text}'...")
                books = db.full_text_search(args.full_text, limit=args.limit)
            else:
                print("🔍 Searching database...")
                books = db.search_books(
                    title=args.title,
                    author=args.author,
                    subject=args.subject,
                    limit=args.limit
                )
        # Default to async mode unless sync mode is explicitly requested
        elif not getattr(args, 'sync_mode', False):
            print("⚡ Using asynchronous search")
            from .async_api_discovery import AsyncAPIBookDiscovery
            discovery_service = AsyncAPIBookDiscovery()
            
            with discovery_service:
                # Perform search based on primary criterion
                if args.title:
                    print(f"🔍 Searching by title: '{args.title}'...")
                    if hasattr(discovery_service, "search_by_title_async"):
                        import asyncio
                        books = asyncio.run(
                            discovery_service.search_by_title_async(args.title, limit=args.limit)
                        )
                    else:
                        books = discovery_service.search_by_title(args.title, limit=args.limit)
                elif args.author:
                    print(f"🔍 Searching by author: '{args.author}'...")
                    if hasattr(discovery_service, "search_by_author_async"):
                        import asyncio
                        books = asyncio.run(
                            discovery_service.search_by_author_async(args.author, limit=args.limit)
                        )
                    else:
                        books = discovery_service.search_by_author(args.author, limit=args.limit)
                else:
                    print("🔍 No primary search criterion (title/author). Falling back to discover...")
                    books = discovery_service.discover_popular_english_epubs(limit=args.limit)
        else:
            print("🔍 Using synchronous search")
            from .api_discovery import APIBookDiscovery
            discovery_service = APIBookDiscovery()
            
            with discovery_service:
                # Perform search based on primary criterion
                if args.title:
                    print(f"🔍 Searching by title: '{args.title}'...")
                    books = discovery_service.search_by_title(args.title, limit=args.limit)
                elif args.author:
                    print(f"🔍 Searching by author: '{args.author}'...")
                    books = discovery_service.search_by_author(args.author, limit=args.limit)
                else:
                    print("🔍 No primary search criterion (title/author). Falling back to discover...")
                    books = discovery_service.discover_popular_english_epubs(limit=args.limit)
        
        # Display results
        if not books:
            print("❌ No books found matching the search criteria")
            return 1
            
        print(f"\n✅ Found {len(books)} books:")
        print("─" * 50)
        
        for i, book in enumerate(books, 1):
            title = book.get("title", "Unknown Title")
            
            # Author varies based on API or DB source
            if "metadata" in book and "author" in book["metadata"]:
                author = book["metadata"]["author"]
            elif "authors" in book:
                # Handle database format
                if isinstance(book["authors"], list) and book["authors"]:
                    author_names = [a["name"] for a in book["authors"] if "name" in a]
                    author = ", ".join(author_names)
                else:
                    author = "Unknown Author"
            else:
                author = book.get("author", "Unknown Author")
                
            book_id = book.get("book_id", "N/A")
            
            # Extract and display key information
            print(f"{i}. [{book_id}] {title}")
            print(f"   Author: {author}")
            
            # Add subjects/categories if available
            if "subjects" in book and book["subjects"]:
                if isinstance(book["subjects"], list):
                    subjects = ", ".join(book["subjects"][:5])
                    if len(book["subjects"]) > 5:
                        subjects += "..."
                    print(f"   Subjects: {subjects}")
            
            # Add download info if available
            if "download_count" in book.get("metadata", {}):
                print(f"   Downloads: {book['metadata']['download_count']}")
                
            # Add formats info if available
            formats = []
            if "formats" in book and book["formats"]:
                if isinstance(book["formats"], dict):
                    formats = list(book["formats"].keys())
                elif isinstance(book["formats"], list):
                    formats = book["formats"]
            elif "download_links" in book and book["download_links"]:
                if isinstance(book["download_links"], dict):
                    formats = list(book["download_links"].keys())
                
            if formats:
                print(f"   Formats: {', '.join(formats[:5])}")
                
            print()
        
        # Save results to file if requested
        if args.output:
            import json
            args.output.parent.mkdir(parents=True, exist_ok=True)
            
            with open(args.output, "w") as f:
                json.dump(books, f, indent=2)
            print(f"📄 Results saved to {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in search command: {e}")
        return 1


def download_command(args: argparse.Namespace) -> int:
    """Execute the download command to download a specific book by ID.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n📚 Book Download")
        print("─" * 50)
        
        print(f"🔍 Downloading book ID: {args.book_id}")
        print(f"📂 Output directory: {args.output}")
        
        # Create output directory if it doesn't exist
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Setup appropriate discovery service
        mirrors_enabled = getattr(args, 'mirrors_enabled', True)
        
        # Default to async mode unless sync mode is explicitly requested
        async_mode = not getattr(args, 'sync_mode', False)
        if async_mode:
            print("⚡ Using asynchronous download")
            if mirrors_enabled:
                print("🔄 Using mirror rotation for downloads")
                
            from .async_api_discovery import AsyncAPIBookDiscovery
            discovery_service = AsyncAPIBookDiscovery()
            
            with discovery_service:
                # Get book details
                import asyncio
                print(f"🔍 Getting details for book {args.book_id}...")
                
                # Check if discovery_service has get_book_by_id method directly
                if hasattr(discovery_service, "get_book_by_id"):
                    book_details = discovery_service.get_book_by_id(args.book_id)
                else:
                    # Use the synchronous method
                    book_details = discovery_service.get_book_details(args.book_id)
                
                if not book_details:
                    print(f"❌ Book ID {args.book_id} not found")
                    return 1
                
                # Generate filename based on title
                title = book_details.get("title", book_details.get("metadata", {}).get("title", f"book_{args.book_id}"))
                author = book_details.get("author", book_details.get("metadata", {}).get("author", "unknown"))
                
                # Clean filename
                clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                clean_title = clean_title.replace(" ", "_")
                filename = f"{clean_title}.epub"
                
                output_path = args.output / filename
                
                print(f"📗 Book Title: {title}")
                print(f"✍️  Author: {author}")
                print(f"📄 Output File: {output_path}")
                
                # Download the book
                print(f"⬇️  Downloading...")
                
                # Fall back to using the synchronous download option which is more reliable
                print("⚠️ Falling back to synchronous download for better reliability")
                from .epub_downloader import EpubDownloader
                
                try:
                    # Create a synchronous downloader with mirror support
                    downloader = EpubDownloader(mirrors_enabled=mirrors_enabled)
                    
                    # Generate direct URL based on book ID (avoid redirect)
                    epub_url = f"https://www.gutenberg.org/cache/epub/{args.book_id}/pg{args.book_id}.epub"
                    
                    # Attempt download
                    success = downloader.download_epub(
                        url=epub_url,
                        output_path=output_path,
                        progress_bar=True,
                        resume=True,
                        book_id=args.book_id
                    )
                    
                    if success:
                        print(f"✅ Successfully downloaded book to {output_path}")
                        return 0
                    else:
                        print(f"❌ Failed to download book {args.book_id}")
                        return 1
                except Exception as e:
                    logger.error(f"Error in download process: {e}")
                    print(f"❌ Failed to download book {args.book_id} due to an error")
                    return 1
        else:
            print("🔍 Using synchronous download")
            if mirrors_enabled:
                print("🔄 Using mirror rotation for downloads")
                
            from .api_discovery import APIBookDiscovery
            discovery_service = APIBookDiscovery()
            
            with discovery_service:
                # Get book details
                print(f"🔍 Getting details for book {args.book_id}...")
                book_details = discovery_service.get_book_details(args.book_id)
                
                if not book_details:
                    print(f"❌ Book ID {args.book_id} not found")
                    return 1
                
                # Generate filename based on title
                title = book_details.get("title", book_details.get("metadata", {}).get("title", f"book_{args.book_id}"))
                author = book_details.get("author", book_details.get("metadata", {}).get("author", "unknown"))
                
                # Clean filename
                clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                clean_title = clean_title.replace(" ", "_")
                filename = f"{clean_title}.epub"
                
                output_path = args.output / filename
                
                print(f"📗 Book Title: {title}")
                print(f"✍️  Author: {author}")
                print(f"📄 Output File: {output_path}")
                
                # Download the book
                print(f"⬇️  Downloading...")
                
                success = False
                if hasattr(discovery_service, "download_book"):
                    success = discovery_service.download_book(
                        args.book_id,
                        output_path,
                        book_details=book_details,
                        resume=True  # Enable resume by default
                    )
                else:
                    # Fallback to download_book_epub if download_book not available
                    success = discovery_service.download_book_epub(
                        args.book_id,
                        output_path,
                        book_details=book_details,
                        resume=True  # Enable resume by default
                    )
                
                if success:
                    print(f"✅ Successfully downloaded book to {output_path}")
                    return 0
                else:
                    print(f"❌ Failed to download book {args.book_id}")
                    return 1
            
    except Exception as e:
        logger.error(f"Error in download command: {e}")
        return 1


def download_popular_command(args: argparse.Namespace) -> int:
    """Execute the download-popular command to download multiple popular books.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n📚 Popular Books Download")
        print("─" * 50)
        
        print(f"🔍 Finding and downloading up to {args.limit} popular books in language '{args.language}'")
        print(f"📂 Output directory: {args.output}")
        
        # Create output directory if it doesn't exist
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Setup appropriate discovery service
        mirrors_enabled = getattr(args, 'mirrors_enabled', True)
        
        # Default to async mode unless sync mode is explicitly requested
        async_mode = not getattr(args, 'sync_mode', False)
        
        if async_mode:
            print("⚡ Using asynchronous discovery and download")
            if mirrors_enabled:
                print("🔄 Using mirror rotation for downloads")
            
            print(f"🔄 Concurrency level: {args.concurrency}")
            
            # Get popular books
            import asyncio
            print(f"🔍 Discovering popular books...")
            
            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Adjust concurrency to be at least 3 and at most 15
            concurrency = max(3, min(args.concurrency, 15))
            
            try:
                # Define a self-contained async function to perform all operations
                async def run_async_operations():
                    from .async_api_discovery import AsyncAPIBookDiscovery
                    
                    # Create a fresh instance each time
                    async with AsyncAPIBookDiscovery(max_concurrency=concurrency) as discovery:
                        # Get the book list
                        books = await discovery.discover_popular_english_epubs_async(limit=args.limit)
                        
                        if not books:
                            return None, None
                        
                        # Extract book IDs
                        book_ids = []
                        book_details = []
                        for book in books:
                            book_ids.append(book.get("book_id"))
                            book_details.append({
                                "id": book.get("book_id"),
                                "title": book.get("title", "Unknown Title"),
                                "author": book.get("metadata", {}).get("author", "Unknown Author")
                            })
                        
                        # Download books in parallel
                        results = await discovery.download_multiple_books_async(
                            book_ids=book_ids,
                            output_dir=args.output,
                            progress_bar=True,
                            skip_existing=True,
                            resume=True  # Enable resume by default
                        )
                        
                        return results, book_details
                
                # Run the entire async operation in one go
                results, book_details = loop.run_until_complete(run_async_operations())
            finally:
                # Make sure to close the loop to free resources
                loop.close()
                
            # Check if no books were found
            if results is None or book_details is None:
                print("❌ No books found")
                return 1
            
            # Display the book details
            print(f"\n✅ Found {len(book_details)} popular books")
            print("─" * 50)
            
            for i, book in enumerate(book_details, 1):
                print(f"{i}. [{book['id']}] {book['title']} by {book['author']}")
            
            print("\n⬇️  Downloads completed...")
            
            # Count successes and failures
            successes = sum(1 for success in results.values() if success)
            failures = sum(1 for success in results.values() if not success)
            
            print("\n─" * 50)
            print(f"✅ Successfully downloaded: {successes}")
            if failures > 0:
                print(f"❌ Failed downloads: {failures}")
            print(f"📂 Books saved to: {args.output}")
            
            return 0 if failures == 0 else 1
                
        else:
            print("🔍 Using synchronous discovery and download (slower but lower resource usage)")
            if mirrors_enabled:
                print("🔄 Using mirror rotation for downloads")
            
            from .api_discovery import APIBookDiscovery
            discovery_service = APIBookDiscovery()
            
            with discovery_service:
                # Get popular books
                print(f"🔍 Discovering popular books...")
                books = discovery_service.discover_popular_english_epubs(limit=args.limit)
                
                if not books:
                    print("❌ No books found")
                    return 1
                
                print(f"\n✅ Found {len(books)} popular books")
                print("─" * 50)
                
                # Download each book
                success_count = 0
                failure_count = 0
                
                for i, book in enumerate(books, 1):
                    book_id = book.get("book_id")
                    title = book.get("title", "Unknown Title")
                    author = book.get("metadata", {}).get("author", "Unknown Author")
                    
                    # Clean filename
                    clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                    clean_title = clean_title.replace(" ", "_")
                    filename = f"{clean_title}.epub"
                    output_path = args.output / filename
                    
                    print(f"\n{i}. [{book_id}] {title} by {author}")
                    print(f"   📄 Output File: {output_path}")
                    
                    # Skip if file already exists
                    if output_path.exists():
                        print(f"   ⏩ Skipping - file already exists")
                        success_count += 1
                        continue
                    
                    # Download the book
                    print(f"   ⬇️  Downloading...")
                    
                    success = False
                    if hasattr(discovery_service, "download_book"):
                        success = discovery_service.download_book(
                            book_id,
                            output_path,
                            book_details=book
                        )
                    else:
                        # Fallback to download_book_epub if download_book not available
                        success = discovery_service.download_book_epub(
                            book_id,
                            output_path,
                            book_details=book
                        )
                    
                    if success:
                        print(f"   ✅ Success")
                        success_count += 1
                    else:
                        print(f"   ❌ Failed")
                        failure_count += 1
                
                print("\n─" * 50)
                print(f"✅ Successfully downloaded: {success_count}")
                if failure_count > 0:
                    print(f"❌ Failed downloads: {failure_count}")
                print(f"📂 Books saved to: {args.output}")
                
                return 0 if failure_count == 0 else 1
            
    except Exception as e:
        logger.error(f"Error in download-popular command: {e}")
        return 1


def filter_download_command(args: argparse.Namespace) -> int:
    """Execute the filter-download command with multiple filtering options.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        # Create output directory if it doesn't exist
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Initialize downloader with mirror support if requested
        mirrors_enabled = getattr(args, 'mirrors_enabled', True)
        database_enabled = getattr(args, 'database_enabled', True)
        resume_enabled = not getattr(args, 'no_resume', False)
        # skip_existing is True by default unless no-skip-existing is specified
        skip_existing = not getattr(args, 'no_skip_existing', False)
        
        with EnhancedDownloader(db_path=args.db_path, mirrors_enabled=mirrors_enabled) as downloader:
            # Parse search terms and subjects
            search_terms = None
            if args.terms:
                search_terms = downloader.normalize_search_terms(args.terms)
                logger.info(f"Search terms: {search_terms}")
            
            subjects = None
            if args.subjects:
                subjects = downloader.normalize_subjects(args.subjects)
                logger.info(f"Subjects: {subjects}")
            
            print(f"\n📚 Enhanced Book Download")
            print(f"📂 Output directory: {args.output}")
            if search_terms:
                print(f"🔍 Search terms: {', '.join(search_terms)}")
            if subjects:
                # Show original subjects
                print(f"🏷️  Subjects: {args.subjects}")
                if len(subjects) > 1:
                    print(f"   🔄 Expanded to: {', '.join(subjects)}")
            print(f"🌐 Language: {args.language}")
            if args.min_downloads:
                print(f"⬇️  Min downloads: {args.min_downloads}")
            if mirrors_enabled:
                print(f"🔄 Mirror sites: Enabled")
            if database_enabled:
                print(f"📊 Database: Enabled")
            if resume_enabled:
                print(f"🔁 Resume capability: Enabled")
            else:
                print(f"🔁 Resume capability: Disabled (--no-resume flag used)")
                
            if skip_existing:
                print(f"⏩ Skip existing files: Enabled")
            else:
                print(f"⏩ Skip existing files: Disabled (--no-skip-existing flag used)")
                
            print(f"📊 Limit: {args.limit}")
            print("─" * 50)
            
            # Check for force_download flag
            force_download = getattr(args, 'force_download', False)
            if force_download:
                print(f"🔄 Force download: Enabled (will redownload existing files)")
            
            # Execute search and download with the initialized skip_existing variable
            success_count, failed_count = downloader.search_and_download(
                search_terms=search_terms,
                language=args.language,
                subjects=subjects,
                min_downloads=args.min_downloads,
                output_dir=args.output,
                limit=args.limit,
                match_any_term=args.match_any,
                skip_existing=skip_existing,
                resume=resume_enabled,
                force_download=force_download
            )
            
            # Print summary
            print("─" * 50)
            print(f"✅ Successfully downloaded: {success_count}")
            if failed_count > 0:
                print(f"❌ Failed downloads: {failed_count}")
            print(f"📂 Books saved to: {args.output}")
            
            return 0 if failed_count == 0 else 1
            
    except Exception as e:
        logger.error(f"Error in filter download: {e}")
        return 1


def db_stats_command(args: argparse.Namespace) -> int:
    """Show database statistics.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n📊 Database Statistics")
        print("─" * 50)
        
        # Initialize database
        from .database import BookDatabase
        db = BookDatabase(db_path=args.db_path)
        
        # Get database statistics
        stats = db.get_statistics()
        
        # Display basic statistics
        print(f"📖 Database File: {args.db_path}")
        if stats.get('database_version'):
            print(f"🔢 Database Version: {stats['database_version']}")
        
        print("\n📚 Content Statistics:")
        print(f"  Total Books: {stats.get('total_books', 0)}")
        print(f"  Total Authors: {stats.get('total_authors', 0)}")
        print(f"  Total Subjects/Categories: {stats.get('total_subjects', 0)}")
        print(f"  Books with EPUB: {stats.get('books_with_epub', 0)}")
        print(f"  Downloaded Books: {stats.get('downloaded_books', 0)}")
        
        # Display language breakdown if available
        if 'languages' in stats and stats['languages']:
            print("\n🌐 Language Breakdown:")
            languages = stats['languages']
            # Sort by count descending
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]:
                if not lang:  # Handle None or empty string
                    lang_display = "Unknown"
                else:
                    lang_display = lang
                print(f"  {lang_display}: {count} books")
            
            if len(languages) > 10:
                print(f"  (and {len(languages) - 10} more languages)")
        
        # Display most popular books if available
        if 'most_popular' in stats and stats['most_popular']:
            print("\n📈 Most Popular Books:")
            for i, book in enumerate(stats['most_popular'][:5], 1):
                title = book.get('title', 'Unknown Title')
                book_id = book.get('book_id', 'N/A')
                downloads = book.get('download_count', 0)
                print(f"  {i}. [{book_id}] {title} - {downloads:,} downloads")
        
        print("\n─" * 50)
        return 0
        
    except Exception as e:
        logger.error(f"Error showing database statistics: {e}")
        return 1


def db_clear_command(args: argparse.Namespace) -> int:
    """Clear the database.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n🗑️  Database Clear")
        print("─" * 50)
        
        import os
        import sqlite3
        
        # Check if the database file exists
        if not os.path.exists(args.db_path):
            print(f"❌ Database file not found: {args.db_path}")
            return 1
        
        # Get file size
        file_size = os.path.getsize(args.db_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"📖 Database File: {args.db_path}")
        print(f"📊 File Size: {file_size_mb:.2f} MB")
        
        # Try to get count of books
        try:
            conn = sqlite3.connect(args.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM books")
            book_count = cursor.fetchone()[0]
            print(f"📚 Contains: {book_count} books")
            conn.close()
        except Exception:
            print("⚠️ Unable to get book count (database may be corrupt or using unknown schema)")
        
        # If not forced, confirm with user
        if not args.force:
            print("\n⚠️ WARNING: This will delete all data in the database!")
            print("To confirm, use the --force flag")
            return 0
        
        # Delete the file
        try:
            os.remove(args.db_path)
            print(f"\n✅ Database {args.db_path} has been deleted.")
            
            # Creating a new empty database
            from .database import BookDatabase
            print(f"🆕 Creating new empty database...")
            BookDatabase(db_path=args.db_path)
            print(f"✅ New empty database created.")
            
            return 0
        except Exception as e:
            print(f"❌ Error deleting database: {e}")
            return 1
            
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return 1


def mirror_status_command(args: argparse.Namespace) -> int:
    """Show mirror site status.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n🔄 Mirror Site Status")
        print("─" * 70)
        
        mirror_manager = MirrorManager()
        mirrors = mirror_manager.get_mirrors()
        
        if not mirrors:
            print("No mirror sites configured")
            return 0
        
        # Get usage statistics
        primary_mirror = next((m for m in mirrors if m.base_url == mirror_manager.primary_site), None)
        primary_name = primary_mirror.name if primary_mirror else "Project Gutenberg Main"
        
        # Get config file path
        config_path = mirror_manager.mirrors_file
        
        # Print summary
        print(f"📊 Summary:")
        print(f"  Total mirror sites: {len(mirrors)}")
        print(f"  Active mirror sites: {sum(1 for m in mirrors if m.active)}")
        print(f"  Primary mirror: {primary_name}")
        print(f"  Configuration: {config_path}")
        if hasattr(mirror_manager, 'recently_used') and mirror_manager.recently_used:
            print(f"  Recently used: {len(mirror_manager.recently_used)} mirrors")
        
        # Check if health assessment is needed or requested
        import time
        current_time = time.time()
        need_health_check = (
            hasattr(args, 'check_health') and args.check_health
        ) or any(
            not m.last_checked or 
            (current_time - m.last_checked > 3600)  # Older than 1 hour
            for m in mirrors
        )
        
        if need_health_check:
            print("\n⏳ Checking mirror health (this may take a few moments)...")
            try:
                health_results = mirror_manager.check_all_mirrors()
                print("✅ Health check completed")
            except Exception as e:
                logger.error(f"Error during health check: {e}")
                print("⚠️ Health check failed, using cached health scores")
                health_results = {m.base_url: True if m.active and m.health_score > 0.5 else False for m in mirrors}
        else:
            print("\n💾 Using cached health status")
            health_results = {m.base_url: True if m.active and m.health_score > 0.5 else False for m in mirrors}
            
        # Print mirror details
        print("\n📋 Mirror Details:")
        print("─" * 70)
        print(f"{'Name':<25} {'Status':<8} {'Health':<8} {'Priority':<8} {'Country':<8} {'Last Check':<15}")
        print("─" * 70)
        
        # Prepare data for display
        mirror_data = []
        for mirror in mirrors:
            # Format last_checked timestamp if available
            if mirror.last_checked:
                import datetime
                last_check = datetime.datetime.fromtimestamp(mirror.last_checked).strftime('%Y-%m-%d %H:%M')
            else:
                last_check = "Never"
                
            # Create health bar visualization
            health_bar = ""
            health_value = mirror.health_score
            if health_value >= 0.8:
                health_bar = "🟢"  # High health (green)
            elif health_value >= 0.5:
                health_bar = "🟡"  # Medium health (yellow)
            elif health_value > 0.1:
                health_bar = "🟠"  # Low health (orange)
            else:
                health_bar = "🔴"  # Critical (red)
                
            # Prepare status indicator
            status = "✅ Active" if mirror.active else "❌ Inactive"
            
            # Add to data for display
            mirror_data.append({
                'mirror': mirror,
                'last_check': last_check,
                'health_bar': health_bar,
                'status': status
            })
        
        # Sort mirrors by priority, then health score
        mirror_data.sort(key=lambda x: (-x['mirror'].priority, -x['mirror'].health_score))
        
        # Display mirror data
        for data in mirror_data:
            mirror = data['mirror']
            health_str = f"{data['health_bar']} {mirror.health_score:.2f}"
            name_display = mirror.name[:25]
            if mirror.base_url == mirror_manager.primary_site:
                name_display = f"* {name_display.strip()}"  # Mark primary mirror
                
            print(f"{name_display:<25} {data['status']:<8} {health_str:<8} {mirror.priority:<8} "
                  f"{mirror.country or 'N/A':<8} {data['last_check']:<15}")
        
        # Print legend
        print("\n🔍 Legend:")
        print("  🟢 High health (0.8-1.0)")
        print("  🟡 Medium health (0.5-0.79)")
        print("  🟠 Low health (0.1-0.49)")
        print("  🔴 Critical (0.0-0.09)")
        print("  * Primary mirror")
        
        # Additional commands help
        print("\n💡 Additional Commands:")
        print("  Update mirror list: gutenberg-downloader mirrors update")
        print("  Use specific mirror: gutenberg-downloader --preferred-mirrors URL download 1342")
        print("  Disable mirrors: gutenberg-downloader --no-mirrors download 1342")
        
        # Save mirrors to preserve health info
        mirror_manager.save_mirrors()
        print("\n💾 Mirror health information saved")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error showing mirror status: {e}")
        return 1


def mirror_update_command(args: argparse.Namespace) -> int:
    """Update mirror list from Project Gutenberg.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n🔄 Updating Mirror List")
        print("─" * 50)
        
        import httpx
        import re
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse
        
        from .constants import DEFAULT_USER_AGENT, REQUEST_TIMEOUT, DEFAULT_MIRRORS_CONFIG_URL
        from .mirror_manager import MirrorManager
        
        print(f"🌐 Checking Project Gutenberg for mirror information...")
        
        # Initialize mirror manager
        mirror_manager = MirrorManager()
        
        # First, try to fetch the MIRRORS.ALL file
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        try:
            # Try to get mirrors from the config URL
            print(f"📥 Fetching mirror list from {DEFAULT_MIRRORS_CONFIG_URL}")
            
            response = httpx.get(DEFAULT_MIRRORS_CONFIG_URL, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            mirrors_text = response.text
            
            # Parse the mirrors text (usually in a format like "Name <URL>")
            mirror_matches = re.findall(r'([^<]+)<([^>]+)>', mirrors_text)
            
            if mirror_matches:
                print(f"✅ Found {len(mirror_matches)} mirrors in MIRRORS.ALL")
                
                # Clear existing mirrors except the primary one
                primary_mirror = next((m for m in mirror_manager.mirrors if m.base_url == mirror_manager.primary_site), None)
                mirror_manager.mirrors = [primary_mirror] if primary_mirror else []
                
                # Add new mirrors
                for name, url in mirror_matches:
                    name = name.strip()
                    url = url.strip()
                    
                    # Skip if URL is empty or invalid
                    if not url or not url.startswith(('http://', 'https://')):
                        continue
                    
                    # Try to detect country from URL or name
                    country = None
                    domain = urlparse(url).netloc.split('.')[-1].upper()
                    if domain and len(domain) == 2:  # Likely a country code
                        country = domain
                    
                    # Assign priority based on TLD or name patterns
                    priority = 2  # Default priority
                    if '.edu' in url or 'university' in name.lower():
                        priority = 3  # Higher priority for education institutions
                    if '.org' in url or 'official' in name.lower():
                        priority = 4  # Higher for official-looking mirrors
                    
                    # Add the mirror
                    mirror_manager.add_mirror(
                        name=name,
                        base_url=url,
                        priority=priority,
                        country=country
                    )
                
                print(f"✅ Added {len(mirror_manager.mirrors) - 1} mirrors from MIRRORS.ALL")
                
            else:
                print("⚠️ Could not find mirrors in MIRRORS.ALL format")
                
                # Try to scrape from the mirrors webpage as a fallback
                print("🔄 Trying to scrape mirrors from Gutenberg website...")
                
                response = httpx.get(
                    "https://www.gutenberg.org/MIRRORS.ALL", 
                    headers=headers, 
                    timeout=REQUEST_TIMEOUT,
                    follow_redirects=True
                )
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for links that might be mirrors
                mirror_links = soup.select('a[href*="gutenberg"]')
                mirror_links.extend(soup.select('a[href*="etext"]'))
                mirror_links.extend(soup.select('a[href*="ebook"]'))
                
                if mirror_links:
                    # Add mirrors found on the page
                    for link in mirror_links:
                        url = link.get('href')
                        name = link.text.strip() or f"Mirror at {urlparse(url).netloc}"
                        
                        # Skip if URL is invalid
                        if not url or not url.startswith(('http://', 'https://')):
                            continue
                        
                        # Skip if it's the main Gutenberg site
                        if 'gutenberg.org' in url:
                            continue
                            
                        # Try to detect country from URL or name
                        country = None
                        domain = urlparse(url).netloc.split('.')[-1].upper()
                        if domain and len(domain) == 2:  # Likely a country code
                            country = domain
                        
                        # Add the mirror
                        mirror_manager.add_mirror(
                            name=name,
                            base_url=url,
                            priority=2,  # Default medium priority
                            country=country
                        )
                    
                    print(f"✅ Added {len(mirror_links)} mirrors from webpage")
                
        except Exception as e:
            print(f"⚠️ Error fetching official mirror list: {e}")
            print("🔍 Using default mirror configuration")
        
        # Check health of all mirrors
        print("\n🔍 Checking mirror health...")
        
        # Use the proper async mirror health checking from MirrorManager
        import asyncio

        # Define an async function to check all mirrors
        async def check_all_mirrors_async():
            """Run async health check on all mirrors."""
            print("\n🔍 Checking mirror health asynchronously...")
            
            # Create mirror checking tasks
            return await mirror_manager.check_all_mirrors_async()
            
        # Run async health checks using asyncio
        print("⏳ Starting mirror health checks...")
        health_results = asyncio.run(check_all_mirrors_async())
        print("✅ Health checks completed")
        
        # Display the results
        for mirror in mirror_manager.mirrors:
            status = "✅" if health_results.get(mirror.base_url, False) else "❌"
            print(f"{status} {mirror.name} ({mirror.base_url})")
                
        print("\n✅ Mirror list updated")
        print(f"📊 Total mirrors: {len(mirror_manager.mirrors)}")
        print(f"📊 Healthy mirrors: {sum(1 for healthy in health_results.values() if healthy)}")
        
        # Display mirror summary
        print("\n📋 Updated Mirror List:")
        print("─" * 70)
        print(f"{'Name':<25} {'URL':<35} {'Health':<10}")
        print("─" * 70)
        
        for mirror in sorted(mirror_manager.mirrors, key=lambda m: (not health_results.get(m.base_url, False), -m.priority)):
            health_status = "✅" if health_results.get(mirror.base_url, False) else "❌"
            print(f"{mirror.name[:25]:<25} {mirror.base_url[:35]:<35} {health_status}")
        
        print("\nTo add custom mirrors, add them to your configuration file or use:")
        print("mirror_manager.add_mirror(name=\"My Mirror\", base_url=\"https://my-mirror.example.com/\")")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error updating mirror list: {e}")
        return 1


def resume_command(args: argparse.Namespace) -> int:
    """Resume interrupted downloads.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        Exit code.
    """
    try:
        print("\n🔄 Resume Interrupted Downloads")
        print("─" * 50)
        
        print(f"📂 Checking directory: {args.output}")
        
        # Create output directory if it doesn't exist
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Setup appropriate discovery service and downloader
        mirrors_enabled = getattr(args, 'mirrors_enabled', True)
        
        # Default to async mode unless sync mode is explicitly requested
        async_mode = not getattr(args, 'sync_mode', False)
        if async_mode:
            print("⚡ Using asynchronous download")
            from .async_epub_downloader import AsyncEpubDownloader
            downloader = AsyncEpubDownloader(mirrors_enabled=mirrors_enabled)
        else:
            print("🔍 Using synchronous download")
            from .epub_downloader import EpubDownloader  
            downloader = EpubDownloader(mirrors_enabled=mirrors_enabled)
            
        if mirrors_enabled:
            print("🔄 Using mirror rotation for downloads")
        
        # Try to load url mapping from database or url cache
        url_mapping = {}
        try:
            # If database exists, try to use it for URL mapping
            import os
            if os.path.exists(args.db_path):
                from .database import BookDatabase
                db = BookDatabase(db_path=args.db_path)
                
                # This is a placeholder - in a real implementation, we would query the
                # database for URLs of previously downloaded books
                print("ℹ️ Found database with download history")
            else:
                print("ℹ️ No database found, using filename-based detection")
                
        except Exception as e:
            logger.warning(f"Error accessing database, falling back to filename detection: {e}")
        
        # Find incomplete downloads
        with downloader:
            print("\n🔍 Searching for incomplete downloads...")
            
            if async_mode:  # async_mode is already defined above
                # For async downloader
                import asyncio
                from .async_epub_downloader import AsyncEpubDownloader  # Import in the function to ensure it's available
                
                # Create a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Define a self-contained async function to perform all operations
                    async def run_async_operations():
                        # Create the downloader inside the async function
                        async with AsyncEpubDownloader(mirrors_enabled=mirrors_enabled) as async_downloader:
                            # Find incomplete downloads
                            incomplete_files = await async_downloader.find_incomplete_downloads(args.output)
                            
                            if not incomplete_files:
                                return None, None
                            
                            # Process file information
                            file_info = []
                            for file_path in incomplete_files:
                                # Try to extract book ID from filename
                                book_id = 0
                                filename = file_path.name
                                if filename.startswith("pg") and filename.endswith(".epub"):
                                    try:
                                        book_id_str = filename[2:].split(".")[0]
                                        if book_id_str.isdigit():
                                            book_id = int(book_id_str)
                                    except (ValueError, IndexError):
                                        book_id = 0
                                
                                # Generate URL from book ID
                                if book_id > 0:
                                    # First try base Project Gutenberg URL
                                    from .constants import BASE_URL
                                    url = f"{BASE_URL}/ebooks/{book_id}.epub"
                                    url_mapping[file_path] = url
                                
                                file_info.append({
                                    "path": file_path,
                                    "name": file_path.name
                                })
                            
                            # Resume downloads in parallel
                            results = await async_downloader.resume_incomplete_downloads(
                                incomplete_files,
                                url_mapping=url_mapping,
                                progress_bar=True
                            )
                            
                            return results, file_info
                    
                    # Run the entire async operation in one go
                    results, file_info = loop.run_until_complete(run_async_operations())
                finally:
                    # Close the event loop
                    loop.close()
                
                # Check if no incomplete files were found
                if results is None or file_info is None:
                    print("✅ No incomplete downloads found")
                    return 0
                
                # Display information about the found files
                print(f"\n🔄 Found {len(file_info)} incomplete downloads:")
                for i, info in enumerate(file_info, 1):
                    print(f"{i}. {info['name']}")
                
                print("\n⬇️ Downloads completed...")
                
                # Count successes and failures
                successes = sum(1 for success in results.values() if success)
                failures = sum(1 for success in results.values() if not success)
                
                print("\n─" * 50)
                print(f"✅ Successfully resumed: {successes}")
                if failures > 0:
                    print(f"❌ Failed to resume: {failures}")
                print(f"📂 Books saved to: {args.output}")
                
                return 0 if failures == 0 else 1
                
            else:
                # For sync downloader
                from .epub_downloader import EpubDownloader  # Import here to make sure it's available
                
                # Create a fresh instance 
                with EpubDownloader(mirrors_enabled=mirrors_enabled) as sync_downloader:
                    # Find incomplete downloads
                    incomplete_files = sync_downloader.find_incomplete_downloads(args.output)
                    
                    if not incomplete_files:
                        print("✅ No incomplete downloads found")
                        return 0
                    
                    print(f"\n🔄 Found {len(incomplete_files)} incomplete downloads:")
                    for i, file_path in enumerate(incomplete_files, 1):
                        print(f"{i}. {file_path.name}")
                        
                        # Try to extract book ID from filename
                        book_id = 0
                        filename = file_path.name
                        if filename.startswith("pg") and filename.endswith(".epub"):
                            try:
                                book_id_str = filename[2:].split(".")[0]
                                if book_id_str.isdigit():
                                    book_id = int(book_id_str)
                            except (ValueError, IndexError):
                                book_id = 0
                        
                        # Generate URL from book ID
                        if book_id > 0:
                            # First try base Project Gutenberg URL
                            from .constants import BASE_URL
                            url = f"{BASE_URL}/ebooks/{book_id}.epub"
                            url_mapping[file_path] = url
                    
                    print("\n⬇️ Resuming downloads...")
                    
                    # Resume downloads sequentially
                    results = sync_downloader.resume_incomplete_downloads(
                        incomplete_files,
                        url_mapping=url_mapping,
                        progress_bar=True
                    )
                    
                    # Count successes and failures
                    successes = sum(1 for success in results.values() if success)
                    failures = sum(1 for success in results.values() if not success)
                    
                    print("\n─" * 50)
                    print(f"✅ Successfully resumed: {successes}")
                    if failures > 0:
                        print(f"❌ Failed to resume: {failures}")
                    print(f"📂 Books saved to: {args.output}")
                    
                    return 0 if failures == 0 else 1
    
    except Exception as e:
        logger.error(f"Error resuming downloads: {e}")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv[1:] if None).
        
    Returns:
        Exit code.
    """
    parser = create_main_parser()
    args = parser.parse_args(argv)
    
    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    setup_logger(level=log_level)
    
    # Execute the requested command
    if not args.command:
        parser.print_help()
        return 0
    
    # Ensure all commands have access to global options
    if not hasattr(args, 'no_mirrors'):
        args.no_mirrors = False
        
    # Set mirrors_enabled based on no_mirrors flag (default is enabled)
    args.mirrors_enabled = not args.no_mirrors
    
    # Set database_enabled based on no_db flag (default is enabled)
    args.database_enabled = not getattr(args, 'no_db', False)
        
    # Main commands
    if args.command == "discover":
        return discover_command(args)
    elif args.command == "search":
        return search_command(args)
    elif args.command == "download":
        return download_command(args)
    elif args.command == "download-popular":
        return download_popular_command(args)
    elif args.command == "filter-download":
        return filter_download_command(args)
    elif args.command == "resume":
        return resume_command(args)
        
    # Database commands
    elif args.command == "db":
        if args.db_command == "stats":
            return db_stats_command(args)
        elif args.db_command == "clear":
            return db_clear_command(args)
        else:
            parser.print_help()
            return 1
            
    # Mirror commands
    elif args.command == "mirrors":
        if args.mirror_command == "status":
            return mirror_status_command(args)
        elif args.mirror_command == "update":
            return mirror_update_command(args)
        else:
            parser.print_help()
            return 1
    else:
        # Unrecognized command
        parser.print_help()
        logger.error(f"Command not implemented: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())