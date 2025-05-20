#!/usr/bin/env python3
"""Direct download script with detailed logging."""

import httpx
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup constants
BOOK_ID = 1342
URL = f"https://www.gutenberg.org/cache/epub/{BOOK_ID}/pg{BOOK_ID}.epub"
OUTPUT_DIR = Path("./direct_download")
OUTPUT_FILE = OUTPUT_DIR / f"book_{BOOK_ID}.epub"

def main():
    """Main download function."""
    # Create directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Setup HTTP client with reasonable headers
    client = httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Direct Download/1.0",
            "Accept": "application/epub+zip, application/octet-stream, */*",
        },
        follow_redirects=True,
        timeout=60.0
    )
    
    try:
        print(f"Downloading {URL} to {OUTPUT_FILE}")
        
        # First, check if the URL is accessible
        print("Checking URL with HEAD request...")
        head_response = client.head(URL)
        head_response.raise_for_status()
        
        file_size = int(head_response.headers.get("content-length", 0))
        print(f"File size: {file_size} bytes")
        print(f"Content type: {head_response.headers.get('content-type', 'unknown')}")
        
        # Now download the file
        print("Starting download...")
        with client.stream("GET", URL) as response:
            response.raise_for_status()
            
            with open(OUTPUT_FILE, "wb") as f:
                total_downloaded = 0
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    total_downloaded += len(chunk)
                    print(f"Downloaded: {total_downloaded}/{file_size} bytes", end="\r")
        
        print(f"\nDownload complete. File saved to {OUTPUT_FILE}")
        
        # Verify file size
        actual_size = OUTPUT_FILE.stat().st_size
        print(f"Downloaded file size: {actual_size} bytes")
        if file_size > 0 and actual_size != file_size:
            print(f"WARNING: Size mismatch. Expected {file_size}, got {actual_size}")
        
    except Exception as e:
        print(f"Error during download: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()