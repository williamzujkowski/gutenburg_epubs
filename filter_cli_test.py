#!/usr/bin/env python3
"""Test CLI integration for filter-download command."""

import sys
import logging
from pathlib import Path
import argparse
from src.gutenberg_downloader.cli import filter_download_command
from src.gutenberg_downloader.logger import setup_logger

# Setup logging
setup_logger(level=logging.INFO)

# Create a namespace object with command line parameters
class Args:
    pass

args = Args()
args.db_path = "gutenberg_books.db"
args.subjects = "science fiction"
args.terms = None
args.language = "en"
args.min_downloads = None
args.output = Path("./cli_test_output")
args.limit = 3
args.match_any = False
args.skip_existing = True

print(f"\n🧪 Testing filter-download command with arguments:")
print(f"Subjects: {args.subjects}")
print(f"Language: {args.language}")
print(f"Output: {args.output}")
print(f"Limit: {args.limit}")
print("─" * 50)

# Run the command
result = filter_download_command(args)

print(f"\nCommand exited with code: {result}")
print("─" * 50)

# Also check registration by running the command directly
import subprocess
print("\nRunning actual command-line interface with filter-download:")
print("─" * 50)
cmd = ["python", "-m", "gutenberg_downloader.cli", "filter-download", "--subjects", "science fiction", "--output", "./cli_cmd_test", "--limit", "1"]
print(f"$ {' '.join(cmd)}")
try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print("Output:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
except Exception as e:
    print(f"Error running command: {e}")