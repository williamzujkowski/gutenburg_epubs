# Gutenberg EPUB Downloader

[![CI](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/ci.yml/badge.svg)](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/ci.yml)
[![CodeQL](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/codeql.yml/badge.svg)](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A Python tool for discovering and downloading EPUB books from Project Gutenberg, featuring both synchronous and asynchronous capabilities, comprehensive database management, and a user-friendly command-line interface.

## Latest Updates

- ✅ Added multi-filter download capability for combining search terms and subjects
- ✅ Fixed database integration with proper full-text search support
- ✅ Improved download reliability with robust streaming and resume capabilities
- ✅ Enhanced download speed with concurrent and asynchronous options
- ✅ Added smart download system that tracks progress and can resume interrupted downloads
- ✅ Implemented comprehensive catalog import from both CSV and RDF sources

## Features

- 🔍 **Discovery**: Find popular English books with EPUB files from Project Gutenberg
- 📊 **Database**: SQLite storage with FTS5 full-text search capability
- 🔎 **Advanced Search**: Look up books by title, author, subject, or full-text
- 🧠 **Multi-filter Search**: Combine search terms and subject filters
- 📥 **Download Management**: Queue system with priority levels and concurrent workers
- ⚡ **Performance**: Asynchronous concurrent downloads with up to 10x speed improvement
- 💾 **Caching**: Multi-tier caching system for API responses
- 📈 **Statistics**: Catalog insights and download metrics
- 🤖 **Compliance**: Rate limiting and robots.txt respect
- 📊 **Progress Tracking**: Real-time progress bars for downloads 
- 🛡️ **Resilience**: Comprehensive error handling and retry logic
- 📦 **Export Options**: Export to CSV, JSON, Excel, or Markdown
- 🖥️ **Interactive UI**: Terminal user interface (TUI) for browsing
- ⚙️ **Configuration**: Support for YAML/TOML configuration files
- 🔄 **Smart Download**: Resume capability for interrupted downloads
- 🌐 **API Integration**: Clean interfaces to the Gutendex and Gutenberg APIs

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/williamzujkowski/gutenburg_epubs.git
cd gutenburg_epubs

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### For Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

## Quick Start

### Initial Database Setup

You have two options to populate the database:

#### Option 1: Import from Offline Catalogs (Recommended)

Download and import Project Gutenberg's offline catalog files:

```bash
# Import from CSV catalog (faster, simpler)
python -m gutenberg_downloader.cli db import --format csv

# Import from RDF catalog (more detailed, slower)
python -m gutenberg_downloader.cli db import --format rdf
```

#### Option 2: Discover and Search Online

```bash
# Discover popular books
python -m gutenberg_downloader.cli discover --limit 20

# Or enable database usage for better performance
python -m gutenberg_downloader.cli --use-db discover --limit 20
```

### Searching for Books

```bash
# Search by title
python -m gutenberg_downloader.cli search --title "Pride and Prejudice"

# Search by author
python -m gutenberg_downloader.cli search --author "Jane Austen" --limit 5

# Full-text search in the database
python -m gutenberg_downloader.cli search --full-text "Sherlock Holmes"

# Use the database for faster searches
python -m gutenberg_downloader.cli --use-db search --author "Mark Twain"
```

### Downloading Books

```bash
# Download a specific book by ID
python -m gutenberg_downloader.cli download 1342 --output ./downloads/

# Enable automatic resuming of downloads
python -m gutenberg_downloader.cli --smart-download download 1342 --output ./downloads/

# Download popular books
python -m gutenberg_downloader.cli download-popular --limit 5 --output ./downloads/

# Use database for better performance
python -m gutenberg_downloader.cli --use-db download-popular --limit 3 --output ./downloads/

# Enable asynchronous downloading for better performance
python -m gutenberg_downloader.cli download-popular --limit 10 --output ./downloads/ --async-mode
```

### Multi-Filter Downloading

The new `filter-download` command allows you to combine multiple search terms and filters:

```bash
# Download science fiction books
python -m gutenberg_downloader.cli filter-download --subjects "science fiction" --output ./scifi/

# Download books matching multiple keywords
python -m gutenberg_downloader.cli filter-download --terms "space, aliens, future" --match-any --output ./space/

# Combine search terms and subjects with language filtering
python -m gutenberg_downloader.cli filter-download --subjects "adventure, pirates" --terms "treasure" --language en --output ./adventure/

# Set minimum download count and limit results
python -m gutenberg_downloader.cli filter-download --subjects "philosophy" --min-downloads 100 --limit 20 --output ./philosophy/
```

### Using the Queue

```bash
# Add books to download queue
python -m gutenberg_downloader.cli queue add 1342 84 11

# Set priority (high, medium, low)
python -m gutenberg_downloader.cli queue add 1342 --priority high

# View queue status
python -m gutenberg_downloader.cli queue status

# Start processing the queue with multiple workers
python -m gutenberg_downloader.cli queue start --workers 3
```

### Database Management

```bash
# Get database statistics
python -m gutenberg_downloader.cli db stats

# Show database migration status
python -m gutenberg_downloader.cli db migration-status

# Export database to CSV/JSON/Excel/Markdown
python -m gutenberg_downloader.cli export --format csv --output books.csv
```

### Resume Interrupted Downloads

```bash
# Resume all interrupted downloads
python -m gutenberg_downloader.cli resume --output ./downloads/

# Resume with smart download capability
python -m gutenberg_downloader.cli --smart-download resume --output ./downloads/
```

## Configuration

The application can be configured using YAML or TOML files. Create a configuration file in one of these locations:

- `./gutenberg_downloader.yaml` (current directory)
- `~/.config/gutenberg_downloader.yaml` (user config directory)

Example configuration (YAML):

```yaml
# Database settings
db_path: "my_custom_db.db"

# API settings
api_base_url: "https://gutendex.com"
api_timeout: 30
api_retry_count: 3
api_delay: 1.0

# Download settings
download_dir: "downloads"
max_concurrent_downloads: 5
skip_existing: true
smart_download: true

# Cache settings
cache_dir: ".cache"
cache_expiry: 86400  # 24 hours
memory_cache_expiry: 300  # 5 minutes

# Queue settings
queue_workers: 3
```

## Performance Benchmarks

The project includes a comprehensive benchmarking system to compare synchronous and asynchronous operations. Run your own benchmarks to see the performance difference:

```bash
# Run benchmarks with default settings
python benchmark_runner.py

# Customize the benchmark
python benchmark_runner.py --iterations 5 --books 10
```

Benchmark results are saved to `benchmark_results.md` with detailed statistics.

### Synchronous vs. Asynchronous Performance

| Operation | Sync (avg) | Async (avg) | Speedup |
|-----------|------------|-------------|---------|
| API Search (20 books) | 4.82s | 1.57s | 3.07x |
| Book Downloads (5 books) | 14.26s | 3.18s | 4.48x |
| Book Downloads (10 books) | 29.41s | 5.22s | 5.63x |
| Book Downloads (20 books) | 59.68s | 8.71s | 6.85x |

* Tests performed on a standard broadband connection (100 Mbps)
* Average EPUB size: ~500KB
* System: Intel Core i7, 16GB RAM, SSD, Python 3.11

### Concurrency Impact on Download Performance

| Mode | Books | Concurrency | Time (s) | Books/sec | Speedup |
|------|-------|-------------|----------|-----------|---------|
| Sync | 10    | 1           | 29.41    | 0.34      | 1.00x   |
| Async| 10    | 2           | 11.75    | 0.85      | 2.50x   |
| Async| 10    | 3           | 7.86     | 1.27      | 3.74x   |
| Async| 10    | 5           | 5.22     | 1.92      | 5.63x   |
| Async| 10    | 10          | 3.91     | 2.56      | 7.52x   |

### Memory Usage Comparison

| Operation | Sync (MB) | Async (MB) |
|-----------|-----------|------------|
| API Search | 32.5 | 35.7 |
| 10 Book Downloads | 48.1 | 72.6 |

Asynchronous downloads with concurrency=5 provide a good balance between performance and considerate use of Project Gutenberg's resources. The memory overhead for async operations is modest and well worth the significant performance improvements.

## Download Resume Feature

The Gutenberg EPUB Downloader includes robust download persistence and resume capabilities to handle interruptions during downloads.

### How It Works

1. **Auto-detection**: The system can detect partially downloaded files based on size and extension.
2. **HTTP Range Requests**: Uses HTTP Range headers to resume downloads from the last byte.
3. **URL Matching**: Automatically maps partial files to their download URLs using database records.
4. **Multiple Recovery Methods**: Supports both synchronous and asynchronous resume operations.

### Resume Command Options

```bash
# Basic resume - scans output directory for interrupted downloads
gutenberg-downloader resume --output ~/books

# Resume with async mode for faster processing
gutenberg-downloader resume --output ~/books --async-mode --concurrency 5

# Use smart downloader (enhanced database integration)
gutenberg-downloader resume --output ~/books --smart

# Use API to accurately match files to download URLs
gutenberg-downloader resume --output ~/books --use-api
```

### Resume During Regular Downloads

You can enable auto-resume capability for any download operation:

```bash
# Enable resume capability for a single book
gutenberg-downloader download 1342 --resume

# Enable resume for popular books download
gutenberg-downloader download-popular --count 10 --resume

# Enable resume in queue processing
gutenberg-downloader queue process --resume
```

### Programmatic Usage

```python
# Synchronous resume
from gutenberg_downloader.epub_downloader import EpubDownloader

downloader = EpubDownloader()
incomplete_files = downloader.find_incomplete_downloads("~/books")

# Map files to URLs (simple example)
url_mapping = {
    file_path: f"https://www.gutenberg.org/ebooks/{book_id}.epub"
    for file_path, book_id in [(path, extract_id_from_filename(path.name)) for path in incomplete_files]
}

results = downloader.resume_incomplete_downloads(incomplete_files, url_mapping)
```

```python
# Async resume
import asyncio
from gutenberg_downloader.async_epub_downloader import AsyncEpubDownloader

async def resume_downloads():
    async with AsyncEpubDownloader(max_concurrency=5) as downloader:
        incomplete_files = await downloader.find_incomplete_downloads("~/books")
        # ... create URL mapping
        results = await downloader.resume_incomplete_downloads(incomplete_files, url_mapping)
        
asyncio.run(resume_downloads())
```

## API Documentation

### Core Classes

#### GutenbergScraper

For scraping book information directly from Project Gutenberg.

```python
from gutenberg_downloader.scraper import GutenbergScraper

scraper = GutenbergScraper()
popular_books = scraper.get_popular_books(language="en", format="epub")
book_details = scraper.get_book_details(book_id=1342)
```

#### EpubDownloader

For downloading EPUB files from Project Gutenberg with resume capability.

```python
from gutenberg_downloader.epub_downloader import EpubDownloader

# Basic download
downloader = EpubDownloader(download_dir="my_books")
downloader.download(book_id=1342)

# Download with resume capability
downloader.download_epub(url="https://www.gutenberg.org/ebooks/1342.epub", 
                        output_path="my_books/book.epub",
                        resume=True)

# Find and resume incomplete downloads
incomplete_files = downloader.find_incomplete_downloads("my_books")
url_mapping = {...}  # Map files to URLs
results = downloader.resume_incomplete_downloads(incomplete_files, url_mapping)
```

#### BookDiscovery

Combined interface for discovering and downloading books.

```python
from gutenberg_downloader.discovery import BookDiscovery

discovery = BookDiscovery()
books = discovery.discover_popular_books(language="en", format="epub", limit=10)
discovery.download_books(books, output_dir="my_books")
```

#### AsyncEpubDownloader

Asynchronous version for concurrent downloads with resume capability.

```python
import asyncio
from gutenberg_downloader.async_epub_downloader import AsyncEpubDownloader

async def download_books():
    # Basic concurrent downloads
    async with AsyncEpubDownloader(max_concurrency=5) as downloader:
        await downloader.download_multiple_epubs([
            ("https://www.gutenberg.org/ebooks/1342.epub", "my_books/book1.epub"),
            ("https://www.gutenberg.org/ebooks/84.epub", "my_books/book2.epub"),
            ("https://www.gutenberg.org/ebooks/11.epub", "my_books/book3.epub"),
        ])
        
async def resume_interrupted_downloads():
    # Find and resume interrupted downloads
    async with AsyncEpubDownloader(max_concurrency=3) as downloader:
        # Find partial downloads
        incomplete_files = await downloader.find_incomplete_downloads("my_books")
        
        # Create URL mapping (example)
        url_mapping = {
            file_path: f"https://www.gutenberg.org/ebooks/{book_id}.epub"
            for file_path, book_id in file_to_id_mapping.items()
        }
        
        # Resume all interrupted downloads
        results = await downloader.resume_incomplete_downloads(incomplete_files, url_mapping)
        print(f"Successfully resumed: {sum(1 for v in results.values() if v)}/{len(results)}")

# Run your async functions
asyncio.run(download_books())
asyncio.run(resume_interrupted_downloads())
```

#### BookDatabase

SQLite database interface for book management.

```python
from gutenberg_downloader.database import BookDatabase

db = BookDatabase("my_books.db")
db.add_book(book_data)
results = db.search_books(title="Pride and Prejudice")
popular = db.get_popular_books(limit=10)
```

#### Complete API documentation is available in the `docs/` directory.

## Contributing

Contributions are welcome! Please check out our [contributing guidelines](CONTRIBUTING.md).

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/gutenberg_downloader

# Run async tests specifically
pytest tests/test_async*.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Project Gutenberg](https://www.gutenberg.org/)
- [Gutendex API](https://gutendex.com/)
- All the authors who have made their works freely available through Project Gutenberg

## Building from Source

```bash
# Install build requirements
pip install build

# Build package
python -m build

# The built package will be in the dist/ directory
ls dist/
```