#!/usr/bin/env python3
"""Test script to check connectivity to Project Gutenberg."""

import httpx
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_connectivity():
    """Test connectivity to various Gutenberg URLs."""
    urls = [
        "https://www.gutenberg.org/",
        "https://www.gutenberg.org/ebooks/1342",
        "https://www.gutenberg.org/ebooks/1342.epub",
        "https://gutenberg.pglaf.org/",
        "https://aleph.pglaf.org/",
        "https://gutenberg.nabasny.com/",
    ]
    
    client = httpx.Client(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Test Script"},
        follow_redirects=True,
        timeout=30.0
    )
    
    for url in urls:
        try:
            print(f"\nTesting connection to: {url}")
            response = client.head(url)
            print(f"Status code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code < 400:
                print("✅ Success!")
            else:
                print("❌ Failed!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    client.close()

if __name__ == "__main__":
    test_connectivity()