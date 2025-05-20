#!/usr/bin/env python3
"""Script to test the fixes implemented in the Gutenberg EPUB Downloader.

This script tests:
1. Regular CLI commands
2. Async mode
3. Mirror site functionality
4. Resume functionality
5. Search functionality
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path

def run_command(command, **kwargs):
    """Run a command and print its output."""
    print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True, **kwargs)
    print(f"Return code: {result.returncode}")
    print("Output:")
    print(result.stdout)
    if result.stderr:
        print("Error:")
        print(result.stderr)
    return result

def test_commands():
    """Test basic CLI commands."""
    print("\n=== Testing Basic Commands ===\n")
    
    # Test version command
    run_command("python -m gutenberg_downloader --version")
    
    # Test discovery
    run_command("python -m gutenberg_downloader discover --limit 3")
    
    # Test search
    run_command("python -m gutenberg_downloader search --title 'Pride and Prejudice' --limit 3")
    
    # Test db stats
    run_command("python -m gutenberg_downloader db stats")
    
    # Test mirrors status
    run_command("python -m gutenberg_downloader mirrors status")

def test_downloads():
    """Test download functionality."""
    print("\n=== Testing Download Commands ===\n")
    
    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # Test regular download
        run_command(f"python -m gutenberg_downloader download 1342 --output {temp_dir}")
        
        # Test download with mirror support
        run_command(f"python -m gutenberg_downloader --use-mirrors download 1661 --output {temp_dir}")
        
        # Test filter download
        run_command(f"python -m gutenberg_downloader filter-download --subjects 'adventure' --limit 2 --output {temp_dir}")
        
        # List downloaded files
        files = list(Path(temp_dir).glob("*.epub"))
        print(f"Downloaded files: {[f.name for f in files]}")
        
        # Verify file content and size
        for file_path in files:
            size = file_path.stat().st_size
            print(f"File: {file_path.name}, Size: {size} bytes")
            # A valid EPUB file should be at least 10KB
            assert size > 10240, f"File {file_path.name} is too small, likely an incomplete download"

def test_async_mode():
    """Test asynchronous mode functionality."""
    print("\n=== Testing Async Mode ===\n")
    
    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # Test async download-popular command
        run_command(f"python -m gutenberg_downloader download-popular --limit 3 --async-mode --output {temp_dir}")
        
        # List downloaded files
        files = list(Path(temp_dir).glob("*.epub"))
        print(f"Downloaded files: {[f.name for f in files]}")
        
        # Verify file content and size
        for file_path in files:
            size = file_path.stat().st_size
            print(f"File: {file_path.name}, Size: {size} bytes")
            # A valid EPUB file should be at least 10KB
            assert size > 10240, f"File {file_path.name} is too small, likely an incomplete download"

def test_mirror_functionality():
    """Test mirror site functionality."""
    print("\n=== Testing Mirror Site Functionality ===\n")
    
    # Test mirror update command
    run_command("python -m gutenberg_downloader mirrors update")
    
    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # Test download with mirror support
        run_command(f"python -m gutenberg_downloader --use-mirrors download 10 --output {temp_dir}")
        
        # Test filter download with mirror support
        run_command(f"python -m gutenberg_downloader --use-mirrors filter-download --subjects 'classics' --limit 2 --output {temp_dir}")
        
        # List downloaded files
        files = list(Path(temp_dir).glob("*.epub"))
        print(f"Downloaded files: {[f.name for f in files]}")
        
        # Verify file content and size
        for file_path in files:
            size = file_path.stat().st_size
            print(f"File: {file_path.name}, Size: {size} bytes")
            # A valid EPUB file should be at least 10KB
            assert size > 10240, f"File {file_path.name} is too small, likely an incomplete download"

def test_resume_functionality():
    """Test resume download functionality."""
    print("\n=== Testing Resume Functionality ===\n")
    
    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # Create an incomplete file by downloading and interrupting
        incomplete_file = Path(temp_dir) / "incomplete.epub"
        with open(incomplete_file, "wb") as f:
            # Write a small amount of data to simulate an incomplete download
            f.write(b"Incomplete download" * 100)
        
        print(f"Created incomplete file: {incomplete_file}")
        
        # Test resume command
        run_command(f"python -m gutenberg_downloader resume --output {temp_dir}")
        
        # Test async resume command
        run_command(f"python -m gutenberg_downloader resume --async-mode --output {temp_dir}")

def main():
    """Run all tests."""
    start_time = time.time()
    
    # Record current directory to return to it
    current_dir = os.getcwd()
    
    try:
        # Change to the project root directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Run tests
        test_commands()
        test_downloads()
        test_async_mode()
        test_mirror_functionality()
        test_resume_functionality()
        
        elapsed = time.time() - start_time
        print(f"\n=== All tests completed in {elapsed:.2f} seconds ===")
        print("✅ Success!")
        return 0
    
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}")
        return 1
    
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        return 1
    
    finally:
        # Return to original directory
        os.chdir(current_dir)

if __name__ == "__main__":
    sys.exit(main())