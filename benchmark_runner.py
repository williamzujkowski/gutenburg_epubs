#!/usr/bin/env python3
"""
Benchmark runner for the gutenberg_downloader package.

This script runs performance benchmarks comparing synchronous vs asynchronous operations.
"""

import argparse
import os
import sys
from pathlib import Path

# Add the current directory to Python path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.gutenberg_downloader.benchmark import run_benchmarks


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark synchronous vs asynchronous operations for Gutenberg Downloader"
    )
    parser.add_argument("-i", "--iterations", type=int, default=3,
                        help="Number of iterations per test (default: 3)")
    parser.add_argument("-b", "--books", type=int, default=5,
                        help="Number of books to use in download tests (default: 5)")
    parser.add_argument("-o", "--output-dir", type=str,
                        help="Directory for test output files")
    
    args = parser.parse_args()
    
    print(f"🚀 Running benchmarks with:")
    print(f"   - {args.iterations} iterations")
    print(f"   - {args.books} books for download tests")
    if args.output_dir:
        print(f"   - Output directory: {args.output_dir}")
    
    run_benchmarks(
        iterations=args.iterations,
        book_count=args.books,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()