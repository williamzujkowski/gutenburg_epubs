#!/usr/bin/env python3
"""Command-line interface for the Gutenberg EPUB downloader.

This module provides CLI functionality for discovering and downloading English ebooks
with EPUB format from Project Gutenberg.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .async_discovery import AsyncBookDiscovery
from .discovery import BookDiscovery
from .logger import setup_logger

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="gutenberg-downloader",
        description="Download English EPUB books from Project Gutenberg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover and list popular English books with EPUB files
  gutenberg-downloader discover --limit 20

  # Download a specific book by ID
  gutenberg-downloader download 123 --output ~/books/

  # Search for books by title
  gutenberg-downloader search --title "Pride and Prejudice"

  # Search for books by author
  gutenberg-downloader search --author "Jane Austen" --limit 10

  # Get catalog statistics
  gutenberg-downloader stats

  # Download multiple popular books
  gutenberg-downloader download-popular --limit 5 --output ~/books/
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output",
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
        help="Available commands",
    )

    # Discover command
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover popular English books with EPUB files",
    )
    discover_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of books to discover (default: 10)",
    )
    discover_parser.add_argument(
        "--format",
        choices=["simple", "detailed"],
        default="simple",
        help="Output format (default: simple)",
    )
    discover_parser.add_argument(
        "--async-mode",
        action="store_true",
        help="Use asynchronous operations for better performance",
    )

    # Download command
    download_parser = subparsers.add_parser(
        "download",
        help="Download a specific book by ID",
    )
    download_parser.add_argument(
        "book_id",
        type=int,
        help="Project Gutenberg book ID",
    )
    download_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)",
    )
    download_parser.add_argument(
        "--filename",
        help="Custom filename for the downloaded EPUB",
    )

    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search for books by title or author",
    )
    search_group = search_parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument(
        "--title",
        help="Search by book title",
    )
    search_group.add_argument(
        "--author",
        help="Search by author name",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    search_parser.add_argument(
        "--exact",
        action="store_true",
        help="Require exact title match",
    )

    # Stats command
    subparsers.add_parser(
        "stats",
        help="Display catalog statistics",
    )

    # Download popular command
    download_popular_parser = subparsers.add_parser(
        "download-popular",
        help="Download multiple popular English EPUB books",
    )
    download_popular_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of books to download (default: 5)",
    )
    download_popular_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)",
    )
    download_popular_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip books that already exist in the output directory",
    )
    download_popular_parser.add_argument(
        "--async-mode",
        action="store_true",
        help="Use asynchronous downloads for better performance",
    )
    download_popular_parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Maximum concurrent downloads (default: 5, only with --async)",
    )

    return parser


def discover_command(args: argparse.Namespace) -> int:
    """Execute the discover command.

    Args:
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    if args.async_mode:
        return asyncio.run(discover_command_async(args))

    try:
        with BookDiscovery() as discovery:
            books = discovery.discover_popular_english_epubs(limit=args.limit)

            if not books:
                logger.info("No English books with EPUB files found.")
                return 0

            if args.format == "simple":
                print(f"Found {len(books)} popular English books with EPUB files:\n")
                for book in books:
                    title = book.get("metadata", {}).get("title", "Unknown Title")
                    author = book.get("metadata", {}).get("author", "Unknown Author")
                    book_id = book.get("book_id", "Unknown")
                    print(f"{book_id}: {title} by {author}")
            else:  # detailed format
                for i, book in enumerate(books, 1):
                    print(f"\n--- Book {i} ---")
                    print(f"ID: {book.get('book_id')}")
                    print(f"Title: {book.get('metadata', {}).get('title')}")
                    print(f"Author: {book.get('metadata', {}).get('author')}")
                    print(f"Language: {book.get('metadata', {}).get('language')}")
                    print(f"EPUB URL: {book.get('download_links', {}).get('epub')}")
                    print(f"Popularity Rank: {book.get('popularity_rank')}")

            return 0

    except Exception as e:
        logger.error(f"Error discovering books: {e}")
        return 1


async def discover_command_async(args: argparse.Namespace) -> int:
    """Execute the discover command asynchronously.

    Args:
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    try:
        async with AsyncBookDiscovery() as discovery:
            books = await discovery.discover_popular_english_epubs_async(limit=args.limit)

            if not books:
                logger.info("No English books with EPUB files found.")
                return 0

            if args.format == "simple":
                print(f"Found {len(books)} popular English books with EPUB files:\n")
                for book in books:
                    title = book.get("metadata", {}).get("title", "Unknown Title")
                    author = book.get("metadata", {}).get("author", "Unknown Author")
                    book_id = book.get("book_id", "Unknown")
                    print(f"{book_id}: {title} by {author}")
            else:  # detailed format
                for i, book in enumerate(books, 1):
                    print(f"\n--- Book {i} ---")
                    print(f"ID: {book.get('book_id')}")
                    print(f"Title: {book.get('metadata', {}).get('title')}")
                    print(f"Author: {book.get('metadata', {}).get('author')}")
                    print(f"Language: {book.get('metadata', {}).get('language')}")
                    print(f"EPUB URL: {book.get('download_links', {}).get('epub')}")
                    print(f"Popularity Rank: {book.get('popularity_rank')}")

            return 0

    except Exception as e:
        logger.error(f"Error discovering books: {e}")
        return 1


def download_command(args: argparse.Namespace) -> int:
    """Execute the download command.

    Args:
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    try:
        # Create output directory if it doesn't exist
        args.output.mkdir(parents=True, exist_ok=True)

        with BookDiscovery() as discovery:
            # Get book details first to get the title for the filename
            book_details = discovery.get_book_details(args.book_id)

            if not book_details:
                logger.error(f"Could not fetch details for book ID {args.book_id}")
                return 1

            # Determine filename
            if args.filename:
                filename = args.filename
                if not filename.endswith(".epub"):
                    filename += ".epub"
            else:
                # Use book title for filename if not specified
                title = book_details.get("metadata", {}).get("title", f"book_{args.book_id}")
                # Clean title for filename
                title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                title = title.replace(" ", "_")
                filename = f"{title}.epub"

            output_path = args.output / filename

            logger.info(f"Downloading book {args.book_id} to {output_path}")

            success = discovery.download_book_epub(
                args.book_id,
                output_path,
                book_details=book_details,
            )

            if success:
                logger.info(f"Successfully downloaded to {output_path}")
                return 0
            else:
                logger.error(f"Failed to download book {args.book_id}")
                return 1

    except Exception as e:
        logger.error(f"Error downloading book: {e}")
        return 1


def search_command(args: argparse.Namespace) -> int:
    """Execute the search command.

    Args:
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    try:
        with BookDiscovery() as discovery:
            if args.title:
                logger.info(f"Searching for books with title: {args.title}")
                results = discovery.search_by_title(
                    args.title,
                    exact_match=args.exact,
                    limit=args.limit,
                )
            else:  # args.author
                logger.info(f"Searching for books by author: {args.author}")
                results = discovery.search_by_author(args.author, limit=args.limit)

            if not results:
                logger.info("No matching books found.")
                return 0

            print(f"Found {len(results)} matching books:\n")
            for book in results:
                title = book.get("metadata", {}).get("title", "Unknown Title")
                author = book.get("metadata", {}).get("author", "Unknown Author")
                book_id = book.get("book_id", "Unknown")
                has_epub = "epub" in book.get("download_links", {})
                epub_status = "EPUB available" if has_epub else "No EPUB"
                print(f"{book_id}: {title} by {author} [{epub_status}]")

            return 0

    except Exception as e:
        logger.error(f"Error searching books: {e}")
        return 1


def stats_command(args: argparse.Namespace) -> int:
    """Execute the stats command.

    Args:
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    _ = args  # Stats command doesn't use args, but interface requires it
    try:
        with BookDiscovery() as discovery:
            logger.info("Gathering catalog statistics...")
            stats = discovery.get_catalog_stats()

            print("\nProject Gutenberg Catalog Statistics")
            print("=" * 35)
            print(f"Total books sampled: {stats['total_books_sampled']}")
            print(f"English books: {stats['english_books']}")
            print(f"Books with EPUB format: {stats['books_with_epub']}")
            print(f"English books with EPUB: {stats['english_books_with_epub']}")

            if stats['total_books_sampled'] > 0:
                english_pct = (stats['english_books'] / stats['total_books_sampled']) * 100
                epub_pct = (stats['books_with_epub'] / stats['total_books_sampled']) * 100
                english_epub_pct = (stats['english_books_with_epub'] / stats['total_books_sampled']) * 100

                print("\nPercentages:")
                print(f"English books: {english_pct:.1f}%")
                print(f"Books with EPUB: {epub_pct:.1f}%")
                print(f"English books with EPUB: {english_epub_pct:.1f}%")

            return 0

    except Exception as e:
        logger.error(f"Error gathering statistics: {e}")
        return 1


def download_popular_command(args: argparse.Namespace) -> int:
    """Execute the download-popular command.

    Args:
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    if args.async_mode:
        return asyncio.run(download_popular_command_async(args))

    try:
        # Create output directory if it doesn't exist
        args.output.mkdir(parents=True, exist_ok=True)

        with BookDiscovery() as discovery:
            logger.info(f"Discovering {args.limit} popular English books with EPUB files...")
            books = discovery.discover_popular_english_epubs(limit=args.limit)

            if not books:
                logger.info("No English books with EPUB files found.")
                return 0

            downloaded_count = 0
            skipped_count = 0

            for i, book in enumerate(books, 1):
                book_id = book.get("book_id")
                title = book.get("metadata", {}).get("title", f"book_{book_id}")

                # Clean title for filename
                clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                clean_title = clean_title.replace(" ", "_")
                filename = f"{clean_title}.epub"
                output_path = args.output / filename

                if args.skip_existing and output_path.exists():
                    logger.info(f"Skipping {book_id}: {title} (already exists)")
                    skipped_count += 1
                    continue

                logger.info(f"Downloading [{i}/{len(books)}] {book_id}: {title}")

                if book_id is not None:
                    success = discovery.download_book_epub(
                        book_id,
                        output_path,
                        book_details=book,
                    )
                else:
                    logger.error(f"No book_id found for book: {title}")
                    success = False

                if success:
                    downloaded_count += 1
                    logger.info(f"Successfully downloaded to {output_path}")
                else:
                    logger.error(f"Failed to download book {book_id}")

            print("\nDownload Summary:")
            print(f"Total books: {len(books)}")
            print(f"Downloaded: {downloaded_count}")
            print(f"Skipped: {skipped_count}")
            print(f"Failed: {len(books) - downloaded_count - skipped_count}")

            return 0

    except Exception as e:
        logger.error(f"Error downloading popular books: {e}")
        return 1


async def download_popular_command_async(args: argparse.Namespace) -> int:
    """Execute the download-popular command asynchronously.

    Args:
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    try:
        # Create output directory if it doesn't exist
        args.output.mkdir(parents=True, exist_ok=True)

        async with AsyncBookDiscovery(max_concurrency=args.concurrency) as discovery:
            logger.info(f"Discovering {args.limit} popular English books with EPUB files...")
            books = await discovery.discover_popular_english_epubs_async(limit=args.limit)

            if not books:
                logger.info("No English books with EPUB files found.")
                return 0

            # Extract book IDs for bulk download
            book_ids = [book["book_id"] for book in books]

            logger.info(f"Starting concurrent download of {len(book_ids)} books...")

            # Download all books concurrently
            results = await discovery.download_multiple_books_async(
                book_ids,
                args.output,
                progress_bar=True,
                skip_existing=args.skip_existing,
                stop_on_error=False,
            )

            # Calculate statistics
            downloaded_count = sum(1 for success in results.values() if success)
            failed_count = sum(1 for success in results.values() if not success)
            total_count = len(book_ids)

            print("\nDownload Summary:")
            print(f"Total books: {total_count}")
            print(f"Downloaded: {downloaded_count}")
            print(f"Failed: {failed_count}")

            return 0

    except Exception as e:
        logger.error(f"Error downloading popular books: {e}")
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv if None).

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    setup_logger(level=log_level)

    # Execute the appropriate command
    commands = {
        "discover": discover_command,
        "download": download_command,
        "search": search_command,
        "stats": stats_command,
        "download-popular": download_popular_command,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
