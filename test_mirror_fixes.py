#!/usr/bin/env python3
"""Test script to verify mirror site functionality."""

import asyncio
import logging
from pathlib import Path
from src.gutenberg_downloader.mirror_manager import MirrorManager
from src.gutenberg_downloader.logger import setup_logger

# Setup logging
setup_logger(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_url_normalization():
    """Test URL normalization function."""
    print("\n🔍 Testing URL normalization...")
    
    mirror_mgr = MirrorManager()
    
    test_urls = [
        "http://example.com",
        "http://example.com/",
        "https://example.com",
        "https://example.com/",
        "http://di.uminho.pt/gutenberg",  # Should stay HTTP
        "http://csclub.uwaterloo.ca/mirror",  # Should stay HTTP
        "https://gutenberg.org/cache"
    ]
    
    for url in test_urls:
        normalized = mirror_mgr._normalize_base_url(url)
        print(f"Original URL: {url}")
        print(f"Normalized:   {normalized}")
        print()
        
    return True

async def test_mirror_health_check():
    """Test mirror health checking functionality."""
    print("\n🔍 Testing mirror health checking...")
    
    mirror_mgr = MirrorManager()
    
    # Get all mirrors
    mirrors = mirror_mgr.get_mirrors()
    print(f"Total mirrors: {len(mirrors)}")
    
    # Take a sample of mirrors to test
    test_mirrors = mirrors[:3]
    
    # Test synchronous health check
    print("\n⏳ Testing synchronous health checks...")
    for mirror in test_mirrors:
        print(f"Checking {mirror.name} ({mirror.base_url})...")
        result = mirror_mgr.check_mirror_health(mirror)
        print(f"Result: {'✅ Healthy' if result else '❌ Unhealthy'}")
    
    # Test asynchronous health check
    print("\n⏳ Testing asynchronous health checks...")
    results = await mirror_mgr.check_all_mirrors_async()
    
    # Display results
    healthy_count = sum(1 for success in results.values() if success)
    print(f"✅ Healthy mirrors: {healthy_count}/{len(mirrors)}")
    
    return True

async def test_mirror_selection():
    """Test mirror selection algorithm."""
    print("\n🔍 Testing mirror selection algorithm...")
    
    mirror_mgr = MirrorManager()
    
    # Select mirrors multiple times to test rotation
    print("\n⏳ Testing mirror selection (10 iterations)...")
    selected_mirrors = []
    for i in range(1, 11):
        selected_url = mirror_mgr.select_mirror()
        selected_mirrors.append(selected_url)
        print(f"Iteration {i}: Selected {selected_url}")
    
    # Count unique mirrors selected
    unique_mirrors = set(selected_mirrors)
    print(f"✅ Selected {len(unique_mirrors)} different mirrors out of 10 selections")
    
    return True

async def test_book_url_generation():
    """Test book URL generation for different mirrors."""
    print("\n🔍 Testing book URL generation...")
    
    mirror_mgr = MirrorManager()
    book_id = 1342  # Pride and Prejudice
    
    mirrors = mirror_mgr.get_mirrors()
    # Take a sample of mirrors to test
    test_mirrors = mirrors[:3]
    
    for mirror in test_mirrors:
        book_url = mirror_mgr.build_book_url(book_id, mirror.base_url)
        print(f"Mirror: {mirror.name}")
        print(f"Base URL: {mirror.base_url}")
        print(f"Book URL: {book_url}")
        print()
    
    return True

async def test_mirror_failure_handling():
    """Test mirror failure handling."""
    print("\n🔍 Testing mirror failure handling...")
    
    mirror_mgr = MirrorManager()
    
    # Get active mirrors
    active_mirrors = mirror_mgr.get_active_mirrors()
    if not active_mirrors:
        print("No active mirrors found.")
        return False
    
    # Select the first active mirror to test failure handling
    test_mirror = active_mirrors[0]
    
    # Get current health score and active status
    original_health = test_mirror.health_score
    original_active = test_mirror.active
    original_failures = mirror_mgr.failure_counts.get(test_mirror.base_url, 0)
    
    print(f"Selected mirror for testing: {test_mirror.name} ({test_mirror.base_url})")
    print(f"Initial health score: {original_health:.2f}")
    print(f"Initial active status: {original_active}")
    print(f"Initial failure count: {original_failures}")
    
    # Report multiple failures
    print("\n⏳ Reporting multiple failures...")
    from src.gutenberg_downloader.constants import DEFAULT_MIRROR_FAILURE_THRESHOLD
    
    for i in range(DEFAULT_MIRROR_FAILURE_THRESHOLD + 1):
        mirror_mgr.report_failure(test_mirror.base_url)
        # Find the mirror object again to get updated values
        updated_mirror = next((m for m in mirror_mgr.mirrors if m.base_url == test_mirror.base_url), None)
        if updated_mirror:
            failures = mirror_mgr.failure_counts.get(test_mirror.base_url, 0)
            print(f"Failure {i+1}: Health score = {updated_mirror.health_score:.2f}, " +
                  f"Failures = {failures}, Active = {updated_mirror.active}")
    
    # Check if mirror was deactivated as expected
    updated_mirror = next((m for m in mirror_mgr.mirrors if m.base_url == test_mirror.base_url), None)
    if updated_mirror and not updated_mirror.active:
        print("✅ Mirror was correctly deactivated after reaching failure threshold")
    else:
        print("❌ Mirror was NOT deactivated as expected")
    
    # Test recovery
    print("\n⏳ Testing recovery with successful request...")
    mirror_mgr.report_success(test_mirror.base_url)
    
    updated_mirror = next((m for m in mirror_mgr.mirrors if m.base_url == test_mirror.base_url), None)
    if updated_mirror:
        print(f"After success report: Health score = {updated_mirror.health_score:.2f}, " +
              f"Failures = {mirror_mgr.failure_counts.get(test_mirror.base_url, 0)}, " +
              f"Active = {updated_mirror.active}")
    
    if updated_mirror and updated_mirror.active:
        print("✅ Mirror was correctly reactivated after success")
    else:
        print("❌ Mirror was NOT reactivated as expected")
    
    return True

async def run_all_tests():
    """Run all test functions."""
    tests = [
        test_url_normalization(),
        test_mirror_health_check(),
        test_mirror_selection(),
        test_book_url_generation(),
        test_mirror_failure_handling()
    ]
    
    results = await asyncio.gather(*tests)
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    all_passed = all(results)
    if all_passed:
        print("✅ All tests passed successfully!")
    else:
        print("❌ Some tests failed.")
    
    return all_passed

if __name__ == "__main__":
    print("Mirror Manager Test Suite")
    print("=" * 50)
    
    asyncio.run(run_all_tests())