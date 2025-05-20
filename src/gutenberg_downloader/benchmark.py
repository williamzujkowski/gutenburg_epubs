"""Performance benchmarking for sync vs async operations."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import statistics
import argparse
import random
import tempfile
import shutil
import sys
import os

from tabulate import tabulate
from tqdm import tqdm

from .api_client import GutendexAPIClient
from .async_api_client import AsyncGutendexAPIClient
from .epub_downloader import EpubDownloader
from .async_epub_downloader import AsyncEpubDownloader
from .api_discovery import APIBookDiscovery
from .async_api_discovery import AsyncAPIBookDiscovery

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class BenchmarkResult:
    """Class to store benchmark results."""
    
    def __init__(self, name: str):
        """Initialize benchmark result.
        
        Args:
            name: Benchmark name
        """
        self.name = name
        self.results: Dict[str, List[float]] = {
            "sync": [],
            "async": []
        }
    
    def add_result(self, method: str, duration: float):
        """Add a result to the benchmark.
        
        Args:
            method: Method type ('sync' or 'async')
            duration: Duration in seconds
        """
        self.results[method].append(duration)
    
    def calculate_statistics(self) -> Dict[str, Dict[str, float]]:
        """Calculate statistics for sync and async results.
        
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        for method, durations in self.results.items():
            if not durations:
                stats[method] = {
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                    "median": 0,
                    "stddev": 0
                }
                continue
                
            stats[method] = {
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
                "median": statistics.median(durations),
                "stddev": statistics.stdev(durations) if len(durations) > 1 else 0
            }
        
        return stats
    
    def speedup_factor(self) -> float:
        """Calculate speedup factor (sync / async).
        
        Returns:
            Speedup factor as a float
        """
        stats = self.calculate_statistics()
        
        if not self.results["async"] or not self.results["sync"]:
            return 0
            
        sync_avg = stats["sync"]["avg"]
        async_avg = stats["async"]["avg"]
        
        if async_avg == 0:
            return float('inf')
            
        return sync_avg / async_avg
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert benchmark result to dictionary.
        
        Returns:
            Dictionary representation
        """
        stats = self.calculate_statistics()
        
        return {
            "name": self.name,
            "sync": {
                "times": self.results["sync"],
                "avg": stats["sync"]["avg"],
                "min": stats["sync"]["min"],
                "max": stats["sync"]["max"],
                "median": stats["sync"]["median"],
                "stddev": stats["sync"]["stddev"]
            },
            "async": {
                "times": self.results["async"],
                "avg": stats["async"]["avg"],
                "min": stats["async"]["min"],
                "max": stats["async"]["max"],
                "median": stats["async"]["median"],
                "stddev": stats["async"]["stddev"]
            },
            "speedup": self.speedup_factor()
        }


class Benchmarker:
    """Class to run benchmarks comparing sync and async operations."""
    
    def __init__(self, iterations: int = 3, output_dir: Optional[Path] = None, cleanup: bool = True):
        """Initialize benchmarker.
        
        Args:
            iterations: Number of iterations for each test
            output_dir: Directory for test output files
            cleanup: Whether to clean up test files
        """
        self.iterations = iterations
        self.output_dir = output_dir or Path(tempfile.mkdtemp())
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.cleanup = cleanup
        self.results: Dict[str, BenchmarkResult] = {}
        
        # Print info
        print(f"📊 Benchmarking with {iterations} iterations")
        print(f"📂 Output directory: {self.output_dir}")
    
    def cleanup_dir(self):
        """Clean up test directory."""
        if self.cleanup and self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            print(f"🧹 Cleaned up directory: {self.output_dir}")
    
    def run_sync_task(self, name: str, task_func: Callable, *args, **kwargs) -> float:
        """Run and time a synchronous task.
        
        Args:
            name: Task name
            task_func: Function to run
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Duration in seconds
        """
        print(f"⏱️  Running sync task: {name}")
        start_time = time.time()
        
        result = task_func(*args, **kwargs)
        
        duration = time.time() - start_time
        print(f"✅ Completed in {duration:.2f} seconds")
        
        return duration
    
    async def run_async_task(self, name: str, task_func: Callable, *args, **kwargs) -> float:
        """Run and time an async task.
        
        Args:
            name: Task name
            task_func: Async function to run
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Duration in seconds
        """
        print(f"⏱️  Running async task: {name}")
        start_time = time.time()
        
        result = await task_func(*args, **kwargs)
        
        duration = time.time() - start_time
        print(f"✅ Completed in {duration:.2f} seconds")
        
        return duration
    
    def benchmark_api_search(self, name: str, search_term: str, limit: int = 10):
        """Benchmark API search operations.
        
        Args:
            name: Benchmark name
            search_term: Search term
            limit: Result limit
        """
        benchmark = BenchmarkResult(name)
        self.results[name] = benchmark
        
        for i in range(self.iterations):
            print(f"\nIteration {i+1}/{self.iterations}")
            
            # Sync
            with GutendexAPIClient() as client:
                duration = self.run_sync_task(
                    f"Sync API search - {search_term}",
                    client.get_english_books_with_epub,
                    limit=limit,
                    search=search_term
                )
                benchmark.add_result("sync", duration)
            
            # Async
            async def run_async_search():
                async with AsyncGutendexAPIClient() as client:
                    return await self.run_async_task(
                        f"Async API search - {search_term}",
                        client.get_english_books_with_epub,
                        limit=limit,
                        search=search_term
                    )
            
            loop = asyncio.get_event_loop()
            duration = loop.run_until_complete(run_async_search())
            benchmark.add_result("async", duration)
    
    def benchmark_book_downloads(self, name: str, book_ids: List[int]):
        """Benchmark book download operations.
        
        Args:
            name: Benchmark name
            book_ids: List of book IDs to download
        """
        benchmark = BenchmarkResult(name)
        self.results[name] = benchmark
        
        for i in range(self.iterations):
            print(f"\nIteration {i+1}/{self.iterations}")
            
            # Create iteration-specific directories
            sync_dir = self.output_dir / f"sync_{i}"
            async_dir = self.output_dir / f"async_{i}"
            sync_dir.mkdir(exist_ok=True)
            async_dir.mkdir(exist_ok=True)
            
            # Sync
            with APIBookDiscovery() as discovery:
                duration = self.run_sync_task(
                    f"Sync downloads - {len(book_ids)} books",
                    self._download_books_sync,
                    discovery,
                    book_ids,
                    sync_dir
                )
                benchmark.add_result("sync", duration)
            
            # Async
            async def run_async_downloads():
                async with AsyncAPIBookDiscovery() as discovery:
                    return await self.run_async_task(
                        f"Async downloads - {len(book_ids)} books",
                        self._download_books_async,
                        discovery,
                        book_ids,
                        async_dir
                    )
            
            loop = asyncio.get_event_loop()
            duration = loop.run_until_complete(run_async_downloads())
            benchmark.add_result("async", duration)
    
    def _download_books_sync(self, discovery: APIBookDiscovery, book_ids: List[int], output_dir: Path) -> int:
        """Helper to download books synchronously.
        
        Args:
            discovery: API discovery instance
            book_ids: List of book IDs
            output_dir: Output directory
            
        Returns:
            Number of successful downloads
        """
        successful = 0
        for book_id in tqdm(book_ids, desc="Downloading books"):
            if discovery.download_book(book_id, str(output_dir / f"{book_id}.epub")):
                successful += 1
        return successful
    
    async def _download_books_async(self, discovery: AsyncAPIBookDiscovery, book_ids: List[int], output_dir: Path) -> int:
        """Helper to download books asynchronously.
        
        Args:
            discovery: Async API discovery instance
            book_ids: List of book IDs
            output_dir: Output directory
            
        Returns:
            Number of successful downloads
        """
        results = await discovery.download_multiple_books_async(
            book_ids,
            output_dir,
            progress_bar=False
        )
        return sum(1 for success in results.values() if success)
    
    def print_results(self):
        """Print benchmark results as a formatted table."""
        if not self.results:
            print("No benchmark results to display.")
            return
        
        table_data = []
        for name, result in self.results.items():
            stats = result.calculate_statistics()
            speedup = result.speedup_factor()
            
            table_data.append([
                name,
                f"{stats['sync']['avg']:.2f}s",
                f"{stats['async']['avg']:.2f}s",
                f"{speedup:.2f}x"
            ])
        
        headers = ["Benchmark", "Sync Avg", "Async Avg", "Speedup"]
        print("\n📊 Benchmark Results:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def generate_markdown_report(self, output_file: Optional[Path] = None) -> str:
        """Generate a detailed Markdown report of benchmark results.
        
        Args:
            output_file: Optional file to write the report
            
        Returns:
            Markdown report as a string
        """
        if not self.results:
            return "No benchmark results to display."
        
        lines = ["# Performance Benchmark Results", ""]
        lines.append("## Test Environment")
        lines.append(f"- Python version: {sys.version.split()[0]}")
        lines.append(f"- OS: {os.name} - {sys.platform}")
        lines.append(f"- Test iterations: {self.iterations}")
        lines.append("")
        
        lines.append("## Summary")
        lines.append("")
        lines.append("| Benchmark | Sync Avg | Async Avg | Speedup |")
        lines.append("|-----------|----------|-----------|---------|")
        
        for name, result in self.results.items():
            stats = result.calculate_statistics()
            speedup = result.speedup_factor()
            
            lines.append(f"| {name} | {stats['sync']['avg']:.2f}s | {stats['async']['avg']:.2f}s | {speedup:.2f}x |")
        
        lines.append("")
        
        lines.append("## Detailed Results")
        for name, result in self.results.items():
            lines.append(f"### {name}")
            stats = result.calculate_statistics()
            
            lines.append("")
            lines.append("#### Synchronous Performance")
            lines.append("- Average: {:.2f}s".format(stats["sync"]["avg"]))
            lines.append("- Minimum: {:.2f}s".format(stats["sync"]["min"]))
            lines.append("- Maximum: {:.2f}s".format(stats["sync"]["max"]))
            lines.append("- Median: {:.2f}s".format(stats["sync"]["median"]))
            if len(result.results["sync"]) > 1:
                lines.append("- Standard Deviation: {:.2f}s".format(stats["sync"]["stddev"]))
            lines.append("")
            
            lines.append("#### Asynchronous Performance")
            lines.append("- Average: {:.2f}s".format(stats["async"]["avg"]))
            lines.append("- Minimum: {:.2f}s".format(stats["async"]["min"]))
            lines.append("- Maximum: {:.2f}s".format(stats["async"]["max"]))
            lines.append("- Median: {:.2f}s".format(stats["async"]["median"]))
            if len(result.results["async"]) > 1:
                lines.append("- Standard Deviation: {:.2f}s".format(stats["async"]["stddev"]))
            lines.append("")
            
            lines.append(f"#### Speedup: {result.speedup_factor():.2f}x")
            lines.append("")
        
        report = "\n".join(lines)
        
        if output_file:
            with open(output_file, "w") as f:
                f.write(report)
            print(f"📝 Report written to {output_file}")
        
        return report


def run_benchmarks(iterations: int = 3, book_count: int = 5, output_dir: Optional[str] = None):
    """Run all benchmarks.
    
    Args:
        iterations: Number of iterations
        book_count: Number of books to download
        output_dir: Output directory
    """
    # Create benchmarker
    benchmarker = Benchmarker(
        iterations=iterations,
        output_dir=Path(output_dir) if output_dir else None
    )
    
    try:
        # Benchmark API search
        print("\n🔍 Benchmarking API Search")
        benchmarker.benchmark_api_search(
            "Book Search",
            "adventure",
            limit=20
        )
        
        # Get some book IDs for download tests
        with GutendexAPIClient() as client:
            popular_books = client.get_english_books_with_epub(limit=50)
            book_ids = [book["id"] for book in popular_books[:book_count]]
        
        # Benchmark downloads
        print("\n📥 Benchmarking Book Downloads")
        benchmarker.benchmark_book_downloads(
            f"Download {book_count} Books",
            book_ids
        )
        
        # Print results
        benchmarker.print_results()
        
        # Generate report
        report_path = Path("benchmark_results.md")
        benchmarker.generate_markdown_report(report_path)
        
    finally:
        # Clean up
        benchmarker.cleanup_dir()


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Benchmark sync vs async operations")
    parser.add_argument("-i", "--iterations", type=int, default=3,
                        help="Number of iterations per test")
    parser.add_argument("-b", "--books", type=int, default=5,
                        help="Number of books to use in download tests")
    parser.add_argument("-o", "--output-dir", type=str,
                        help="Directory for test output files")
    
    args = parser.parse_args()
    
    run_benchmarks(
        iterations=args.iterations,
        book_count=args.books,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()