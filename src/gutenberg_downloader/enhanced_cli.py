"""Enhanced CLI command for multi-filter book discovery and download."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .enhanced_downloader import EnhancedDownloader
from .logger import setup_logger

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
        """,
    )
    
    # Basic options
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("downloads"),
        help="Output directory for downloaded books (default: downloads)",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of books to download (default: 10)"
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default="gutenberg_books.db",
        help="Path to database file (default: gutenberg_books.db)",
    )
    
    # Search and filter options
    parser.add_argument(
        "--terms",
        type=str,
        help="Search terms (comma-separated or quoted strings)",
    )
    
    parser.add_argument(
        "--subject",
        type=str,
        help="Filter by subjects/genres (comma-separated or quoted strings)",
    )
    
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Filter by language code (default: en)",
    )
    
    parser.add_argument(
        "--min-downloads",
        type=int,
        help="Minimum download count",
    )
    
    parser.add_argument(
        "--match-any",
        action="store_true",
        help="Match books with any of the search terms (default: must match all terms)",
    )
    
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip books that already exist in the output directory",
    )
    
    # Mirror options
    parser.add_argument(
        "--use-mirrors",
        action="store_true",
        help="Use mirror site rotation to avoid rate limits and speed up downloads",
    )
    
    parser.add_argument(
        "--preferred-mirrors",
        type=str,
        help="Comma-separated list of preferred mirror URLs",
    )
    
    # Output options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-error output",
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
                skip_existing=args.skip_existing
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
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    setup_logger(level=log_level)
    
    return enhanced_download_command(args)


if __name__ == "__main__":
    sys.exit(main())