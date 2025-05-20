"""Enhanced CLI command for multi-filter book discovery and download."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .enhanced_downloader import EnhancedDownloader
from .logger import setup_logger
from .tui import run_tui

logger = logging.getLogger(__name__)


def create_enhanced_parser() -> argparse.ArgumentParser:
    """Create parser for the enhanced download command.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="gutenberg-enhanced-download",
        description="Download Project Gutenberg books with advanced filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download science fiction books
  gutenberg-enhanced-download --subject "science fiction" --output ./scifi_books/
  
  # Download books matching multiple terms
  gutenberg-enhanced-download --terms "space, aliens, future" --match-any --output ./space_books/
  
  # Download books with specific subjects and search terms
  gutenberg-enhanced-download --subject "adventure, pirates" --terms "treasure" --output ./pirate_books/
  
  # Filter by language and minimum downloads
  gutenberg-enhanced-download --subject "philosophy" --language fr --min-downloads 100 --output ./french_philosophy/
  
  # Launch the interactive Terminal User Interface
  gutenberg-enhanced-download --tui
  
  # Update metadata for existing downloads
  gutenberg-enhanced-download --refresh-metadata --output ./downloads/ --verbose
        """,
    )
    
    # Command mode - subparsers for different operations
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Download command (default)
    download_parser = subparsers.add_parser("download", help="Download books (default)")
    
    # Metadata command
    metadata_parser = subparsers.add_parser("metadata", help="Update/refresh metadata for books")
    metadata_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh metadata for books in the database",
    )
    metadata_parser.add_argument(
        "--sync-dir",
        type=Path,
        help="Directory containing previously downloaded books to update metadata for",
    )
    metadata_parser.add_argument(
        "--force",
        action="store_true",
        help="Force metadata refresh even for books already up-to-date",
    )
    metadata_parser.add_argument(
        "--source",
        type=str,
        choices=["api", "csv", "rdf", "all"],
        default="api",
        help="Metadata source to use for refresh (default: api)",
    )
    metadata_parser.add_argument(
        "--db-path",
        type=str,
        default="gutenberg_books.db",
        help="Path to database file (default: gutenberg_books.db)",
    )
    metadata_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    metadata_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of books to update (default: no limit)",
    )
    
    # Basic options (for download command and top-level)
    for p in [parser, download_parser]:
        p.add_argument(
            "--output", "-o",
            type=Path,
            default=Path("downloads"),
            help="Output directory for downloaded books (default: downloads)",
        )
        
        p.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of books to download (default: 10)"
        )
        
        p.add_argument(
            "--db-path",
            type=str,
            default="gutenberg_books.db",
            help="Path to database file (default: gutenberg_books.db)",
        )
        
        # Search and filter options
        p.add_argument(
            "--terms",
            type=str,
            help="Search terms (comma-separated or quoted strings)",
        )
        
        p.add_argument(
            "--subject",
            type=str,
            help="Filter by subjects/genres (comma-separated or quoted strings)",
        )
        
        p.add_argument(
            "--language",
            type=str,
            default="en",
            help="Filter by language code (default: en)",
        )
        
        p.add_argument(
            "--min-downloads",
            type=int,
            help="Minimum download count",
        )
        
        p.add_argument(
            "--match-any",
            action="store_true",
            help="Match books with any of the search terms (default: must match all terms)",
        )
        
        p.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip books that already exist in the output directory",
        )
        
        p.add_argument(
            "--tui",
            action="store_true",
            help="Launch the interactive Terminal User Interface",
        )
        
        p.add_argument(
            "--force-download",
            action="store_true",
            help="Force download even if files already exist (for testing mirror fallback)",
        )
        
        p.add_argument(
            "--no-mirrors",
            action="store_true",
            help="Disable mirror site rotation (enabled by default)",
        )
        
        p.add_argument(
            "--max-workers",
            type=int,
            default=3,
            help="Maximum number of concurrent downloads (default: 3)",
        )
        
        # Mirror options
        p.add_argument(
            "--use-mirrors",
            action="store_true",
            help="Use mirror site rotation to avoid rate limits and speed up downloads",
        )
        
        p.add_argument(
            "--preferred-mirrors",
            type=str,
            help="Comma-separated list of preferred mirror URLs",
        )
        
        # Output options
        p.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output",
        )
        
        p.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Suppress non-error output",
        )
    
    # For compatibility with existing CLI, add a refresh metadata flag to top-level
    parser.add_argument(
        "--refresh-metadata",
        action="store_true",
        help="Refresh metadata for books in specified output directory",
    )
    
    return parser


def enhanced_download_command(args: argparse.Namespace) -> int:
    """Execute the enhanced download command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        # Parse search terms
        search_terms = None
        if args.terms:
            downloader = EnhancedDownloader(db_path=args.db_path)
            search_terms = downloader.normalize_search_terms(args.terms)
            logger.info(f"Search terms: {search_terms}")
        
        # Parse subjects
        subjects = None
        if args.subject:
            downloader = EnhancedDownloader(db_path=args.db_path)
            subjects = downloader.normalize_subjects(args.subject)
            logger.info(f"Subjects: {subjects}")
        
        # Create output directory
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Initialize downloader with mirror support if requested
        mirrors_enabled = getattr(args, 'use_mirrors', False)
        with EnhancedDownloader(db_path=args.db_path, mirrors_enabled=mirrors_enabled) as downloader:
            print(f"\n📚 Enhanced Book Download")
            print(f"📂 Output directory: {args.output}")
            if search_terms:
                print(f"🔍 Search terms: {', '.join(search_terms)}")
            if subjects:
                print(f"🏷️  Subjects: {', '.join(subjects)}")
            print(f"🌐 Language: {args.language}")
            if args.min_downloads:
                print(f"⬇️  Min downloads: {args.min_downloads}")
            if mirrors_enabled:
                print(f"🔄 Mirror sites: Enabled")
            print(f"📊 Limit: {args.limit}")
            print("─" * 50)
            
            # Execute search and download
            success_count, failed_count = downloader.search_and_download(
                search_terms=search_terms,
                language=args.language,
                subjects=subjects,
                min_downloads=args.min_downloads,
                output_dir=args.output,
                limit=args.limit,
                match_any_term=args.match_any,
                skip_existing=args.skip_existing,
                force_download=getattr(args, 'force_download', False)
            )
            
            # Print summary
            print("─" * 50)
            print(f"✅ Successfully downloaded: {success_count}")
            if failed_count > 0:
                print(f"❌ Failed downloads: {failed_count}")
            print(f"📂 Books saved to: {args.output}")
            
        return 0 if failed_count == 0 else 1
    
    except Exception as e:
        logger.error(f"Error in enhanced download: {e}")
        return 1


def metadata_refresh_command(args: argparse.Namespace) -> int:
    """Execute the metadata refresh command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        from .database import BookDatabase
        from .api_discovery import APIBookDiscovery
        from .catalog_importer import CatalogImporter
        import os
        from tqdm import tqdm
        import glob
        
        print(f"\n📚 Enhanced Metadata Refresh")
        
        # Initialize database
        db = BookDatabase(db_path=args.db_path)
        
        # If a sync directory is specified, find all EPUB files and extract book IDs
        book_ids = []
        if getattr(args, 'sync_dir', None) or (hasattr(args, 'output') and args.refresh_metadata):
            sync_dir = getattr(args, 'sync_dir', args.output)
            print(f"🔍 Scanning directory: {sync_dir}")
            
            # Use glob to find all EPUB files
            epub_files = glob.glob(f"{sync_dir}/**/*.epub", recursive=True)
            
            # For each EPUB file, try to extract the book ID from the filename or metadata
            from zipfile import ZipFile
            for epub_file in tqdm(epub_files, desc="Scanning EPUB files"):
                try:
                    # Try to extract book ID from the EPUB metadata
                    book_id = None
                    
                    # First, check if the book exists in the database and matches the filename
                    basename = os.path.basename(epub_file)
                    # Remove extension and clean up filename
                    basename = os.path.splitext(basename)[0].replace('_', ' ').lower()
                    
                    # Search for books with similar titles
                    with db._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT book_id, title FROM books 
                            WHERE LOWER(title) LIKE ? 
                            ORDER BY download_count DESC
                            LIMIT 1
                        """, (f"%{basename}%",))
                        result = cursor.fetchone()
                        if result:
                            book_id = result['book_id']
                    
                    if book_id:
                        book_ids.append(book_id)
                except Exception as e:
                    logger.warning(f"Error processing {epub_file}: {e}")
            
            print(f"📊 Found {len(book_ids)} books to refresh metadata")
        else:
            # Otherwise, just refresh all books in the database
            print(f"📊 Refreshing metadata for all books in database")
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT book_id FROM books")
                book_ids = [row['book_id'] for row in cursor.fetchall()]
        
        # Apply limit if specified
        if getattr(args, 'limit', None) and len(book_ids) > args.limit:
            print(f"⚠️  Limiting to {args.limit} books (out of {len(book_ids)})")
            book_ids = book_ids[:args.limit]
        
        # Initialize API client for metadata refresh
        with APIBookDiscovery() as api:
            # Process each book
            updated = 0
            failed = 0
            skipped = 0
            
            print(f"🔄 Refreshing metadata for {len(book_ids)} books...")
            for book_id in tqdm(book_ids, desc="Refreshing metadata"):
                try:
                    # Skip if not forcing refresh and metadata_version is already 2
                    if not getattr(args, 'force', False):
                        with db._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT metadata_version FROM books 
                                WHERE book_id = ? AND metadata_version = 2
                            """, (book_id,))
                            if cursor.fetchone():
                                skipped += 1
                                continue
                    
                    # Get book metadata from API
                    book_data = api.get_book_by_id(book_id)
                    if book_data:
                        # Update book in database
                        if db.insert_book(book_data):
                            updated += 1
                        else:
                            failed += 1
                    else:
                        logger.warning(f"Metadata not found for book {book_id}")
                        failed += 1
                except Exception as e:
                    logger.error(f"Error refreshing metadata for book {book_id}: {e}")
                    failed += 1
        
        # Print summary
        print("─" * 50)
        print(f"✅ Successfully updated: {updated}")
        if skipped > 0:
            print(f"⏭️  Skipped (already up-to-date): {skipped}")
        if failed > 0:
            print(f"❌ Failed updates: {failed}")
        
        return 0 if failed == 0 else 1
    
    except Exception as e:
        logger.error(f"Error in metadata refresh: {e}")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the enhanced CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv if None).
        
    Returns:
        Exit code.
    """
    parser = create_enhanced_parser()
    args = parser.parse_args(argv)
    
    # Setup logging
    if getattr(args, 'quiet', False):
        log_level = logging.ERROR
    elif getattr(args, 'verbose', False):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    setup_logger(level=log_level)
    
    # Check if we should launch the TUI
    if getattr(args, 'tui', False):
        logger.info("Launching Terminal User Interface")
        try:
            # Configure TUI settings from args
            run_tui(
                db_path=args.db_path,
                mirrors_enabled=not getattr(args, 'no_mirrors', False),
                output_dir=str(args.output),
                max_workers=getattr(args, 'max_workers', 3)
            )
            return 0
        except Exception as e:
            logger.error(f"Error in TUI: {e}")
            return 1
    
    # Check if we're in refresh-metadata mode
    if getattr(args, 'refresh_metadata', False):
        return metadata_refresh_command(args)
    
    # Check which command to run
    if getattr(args, 'command', None) == 'metadata':
        return metadata_refresh_command(args)
    
    # Standard download command (default)
    return enhanced_download_command(args)


if __name__ == "__main__":
    sys.exit(main())