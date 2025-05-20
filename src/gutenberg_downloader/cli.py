#!/usr/bin/env python3
"""Command-line interface for the Gutenberg EPUB downloader.

This module provides CLI functionality for discovering and downloading English ebooks
with EPUB format from Project Gutenberg.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from . import __version__
from .api_discovery import APIBookDiscovery
from .async_api_discovery import AsyncAPIBookDiscovery
from .async_discovery import AsyncBookDiscovery
from .discovery import BookDiscovery
from .logger import setup_logger
from .api_discovery_db import APIBookDiscoveryDB
from .database import BookDatabase
from .enhanced_downloader import EnhancedDownloader

logger = logging.getLogger(__name__)


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
        
        with EnhancedDownloader(db_path=args.db_path) as downloader:
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
                # Show original and expanded subjects
                print(f"🏷️  Subjects: {args.subjects}")
                if len(subjects) > 1:
                    print(f"   🔄 Expanded to: {', '.join(subjects)}")
            print(f"🌐 Language: {args.language}")
            if args.min_downloads:
                print(f"⬇️  Min downloads: {args.min_downloads}")
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