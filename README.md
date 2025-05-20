# Gutenberg EPUB Downloader

[![CI](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/ci.yml/badge.svg)](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/ci.yml)
[![CodeQL](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/codeql.yml/badge.svg)](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A Python tool for discovering and downloading EPUB books from Project Gutenberg, featuring both synchronous and asynchronous capabilities, comprehensive database management, and a user-friendly command-line interface.

## Latest Updates

- ✅ Completed comprehensive CLI with support for all major commands
- ✅ Enhanced mirror site support with persistent health tracking and automatic updates
- ✅ Fixed global `--use-mirrors` flag to work with all commands
- ✅ Improved mirror selection algorithm with weighted health-based selection
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
- 🔄 **Mirror Site Rotation**: Distribute downloads across multiple Gutenberg mirrors
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

### Database Setup

The database will be created automatically when needed. You can populate it through regular usage of the discovery and search commands:

#### Using Discovery and Search

```bash
# Discover popular books
gutenberg-downloader discover --limit 20

# Or enable database usage for better performance
gutenberg-downloader --use-db discover --limit 20
```

### Searching for Books

```bash
# Search by title
gutenberg-downloader search --title "Pride and Prejudice"

# Search by author
gutenberg-downloader search --author "Jane Austen" --limit 5

# Full-text search in the database
gutenberg-downloader search --full-text "Sherlock Holmes"

# Use the database for faster searches
gutenberg-downloader --use-db search --author "Mark Twain"
```

### Downloading Books

```bash
# Download a specific book by ID
gutenberg-downloader download 1342 --output ./downloads/

# Download with mirror site support for faster, limit-avoiding downloads
gutenberg-downloader --use-mirrors download 1342 --output ./downloads/

# Download popular books
gutenberg-downloader download-popular --limit 5 --output ./downloads/

# Use database for better performance
gutenberg-downloader --use-db download-popular --limit 3 --output ./downloads/

# Enable asynchronous downloading for better performance
gutenberg-downloader download-popular --limit 10 --output ./downloads/ --async-mode

# Set concurrency level for async downloads
gutenberg-downloader download-popular --limit 20 --async-mode --concurrency 5 --output ./downloads/
```

### Multi-Filter Downloading

The `filter-download` command allows you to combine multiple search terms and filters:

```bash
# Download science fiction books
gutenberg-downloader filter-download --subjects "science fiction" --output ./scifi/

# Download books matching multiple keywords
gutenberg-downloader filter-download --terms "space, aliens, future" --match-any --output ./space/

# Combine search terms and subjects with language filtering
gutenberg-downloader filter-download --subjects "adventure, pirates" --terms "treasure" --language en --output ./adventure/

# Set minimum download count and limit results
gutenberg-downloader filter-download --subjects "philosophy" --min-downloads 100 --limit 20 --output ./philosophy/
```

### Using Mirror Sites for Better Downloads

```bash
# Enable mirror site rotation with default settings
gutenberg-downloader --use-mirrors download-popular --limit 10 --output ./downloads/

# Specify preferred mirrors in config or command line
gutenberg-downloader --preferred-mirrors "https://gutenberg.pglaf.org/,https://aleph.pglaf.org/" download 1342

# Get mirror site status
gutenberg-downloader mirrors status

# Update mirror list from Project Gutenberg
gutenberg-downloader mirrors update
```

### Command Overview

Here's a summary of available commands:

```
discover              - Find popular books with EPUB format
search                - Search for books by title, author, or subject
download              - Download a specific book by ID
download-popular      - Download multiple popular books
filter-download       - Download books with advanced filtering
resume                - Resume interrupted downloads
db stats              - Show database statistics
db clear              - Clear the database (use --force to skip confirmation)
mirrors status        - Show mirror site status
mirrors update        - Update mirror list from Project Gutenberg
```

Global options available for most commands:
```
--verbose, -v         - Enable verbose output
--quiet, -q           - Suppress non-error output
--use-db              - Use database for operations
--db-path             - Path to database file (default: gutenberg_books.db)
--use-mirrors         - Use mirror site rotation to avoid rate limits
--preferred-mirrors   - Comma-separated list of preferred mirror URLs
```

### Database Management

```bash
# Get database statistics
gutenberg-downloader db stats

# Clear database (with confirmation prompt)
gutenberg-downloader db clear

# Force clear database without confirmation
gutenberg-downloader db clear --force
```

### Resume Interrupted Downloads

```bash
# Resume all interrupted downloads
gutenberg-downloader resume --output ./downloads/

# Resume with asynchronous processing
gutenberg-downloader resume --output ./downloads/ --async-mode

# Resume with mirror site rotation for faster downloads
gutenberg-downloader --use-mirrors resume --output ./downloads/
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
api:
  base_url: "https://gutendex.com"
  timeout: 30
  retry_count: 3
  delay: 1.0

# Download settings
download:
  dir: "downloads"
  max_concurrent: 5
  skip_existing: true
  smart_download: true

# Mirror settings
mirrors:
  enabled: true
  preferred_mirrors:
    - https://gutenberg.pglaf.org/
    - https://aleph.pglaf.org/
    - https://gutenberg.nabasny.com/
  excluded_mirrors: []
  preferred_countries:
    - US
    - CA
  auto_update: true  # Automatically update mirrors list periodically
  save_health_data: true  # Persist mirror health information between runs
  health_check_interval: 3600  # Check mirror health every hour (in seconds)

# Cache settings
cache:
  dir: ".cache"
  expiry: 86400  # 24 hours
  memory_expiry: 300  # 5 minutes

# Queue settings
queue:
  workers: 3
```

## Mirror Site Support

The Gutenberg EPUB Downloader now includes robust support for mirror sites to:

1. **Distribute Load**: Avoid hitting rate limits from a single server by rotating between multiple mirrors
2. **Improve Speed**: Select faster mirrors based on response time and health
3. **Increase Reliability**: Continue working even if some mirrors are down

### How Mirror Selection Works

The system intelligently selects the best mirror for each download based on:

1. **Health Score**: Each mirror gets a health score based on response time and reliability
2. **Priority**: Some mirrors are prioritized over others (can be customized)
3. **Recent Usage**: The system avoids using the same mirror repeatedly in a short timeframe
4. **Book Availability**: Only mirrors known to have the specific book are selected
5. **User Preferences**: You can specify preferred mirrors and countries in the configuration

### Mirror Site Capabilities

- **Automatic Rotation**: Seamlessly switch between mirrors if one fails
- **Health Tracking**: Continuously monitor mirror health and adjust preferences with persistent health data
- **Failed Request Handling**: Automatically retry with a different mirror if a download fails
- **Country-Based Selection**: Prefer mirrors in specific countries for better performance
- **Weighted Selection**: Intelligent mirror choice based on health score, priority, and recent usage
- **Auto-Discovery**: Update mirror list from Project Gutenberg's MIRRORS.ALL file
- **Health Persistence**: Mirror health data is saved between runs in user's home directory
- **Configuration Options**: Extensive customization through YAML config

### Programming with Mirrors

```python
from gutenberg_downloader import EpubDownloader, MirrorManager

# Use the mirror manager directly
mirror_mgr = MirrorManager()
book_url = mirror_mgr.get_book_url(book_id=1342)

# Or enable mirrors in the downloader
downloader = EpubDownloader(mirrors_enabled=True)
success = downloader.download_epub(
    url="https://www.gutenberg.org/ebooks/1342.epub",
    output_path="downloads/pride_and_prejudice.epub",
    book_id=1342  # Providing book_id enables mirror selection
)
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

### Mirror Site Performance Impact

| Mode | Books | Mirrors | Concurrency | Time (s) | Books/sec | Speedup |
|------|-------|---------|-------------|----------|-----------|---------|
| Sync | 10    | No      | 1           | 29.41    | 0.34      | 1.00x   |
| Sync | 10    | Yes     | 1           | 25.15    | 0.40      | 1.17x   |
| Async| 10    | No      | 5           | 5.22     | 1.92      | 5.63x   |
| Async| 10    | Yes     | 5           | 3.87     | 2.58      | 7.60x   |

Mirror site rotation can provide significant benefits:
- Avoids rate limits when downloading many books
- Better average response time by selecting faster mirrors
- Increased reliability as failed downloads retry on different mirrors
- Scales better for bulk downloads (50+ books)

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
gutenberg-downloader resume --output ~/books --async-mode

# Use database integration for better filename matching
gutenberg-downloader --use-db resume --output ~/books

# Use mirror site rotation for faster, more reliable resumes (global flag)
gutenberg-downloader --use-mirrors resume --output ~/books

# Combine async mode with mirrors for maximum performance
gutenberg-downloader --use-mirrors resume --output ~/books --async-mode
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

downloader = EpubDownloader(mirrors_enabled=True)
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
    async with AsyncEpubDownloader(max_concurrency=5, mirrors_enabled=True) as downloader:
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
downloader = EpubDownloader(download_dir="my_books", mirrors_enabled=True)
downloader.download(book_id=1342)

# Download with resume capability
downloader.download_epub(url="https://www.gutenberg.org/ebooks/1342.epub", 
                        output_path="my_books/book.epub",
                        resume=True,
                        book_id=1342)

# Find and resume incomplete downloads
incomplete_files = downloader.find_incomplete_downloads("my_books")
url_mapping = {...}  # Map files to URLs
results = downloader.resume_incomplete_downloads(incomplete_files, url_mapping)
```

#### MirrorManager

For managing and rotating between different Gutenberg mirror sites.

```python
from gutenberg_downloader.mirror_manager import MirrorManager

# Initialize the mirror manager
mirror_mgr = MirrorManager()

# Get the URL for a specific book using the best available mirror
book_url = mirror_mgr.get_book_url(book_id=1342)

# Add a custom mirror
mirror_mgr.add_mirror(
    name="My Custom Mirror", 
    base_url="https://my-gutenberg-mirror.example.com/",
    priority=3,
    country="FR"
)

# Report mirror health
mirror_mgr.report_success("https://gutenberg.pglaf.org/")
mirror_mgr.report_failure("https://slow-mirror.example.com/")

# Check health of all mirrors (synchronous version)
health_status = mirror_mgr.check_all_mirrors()

# Check health of all mirrors (asynchronous version)
import asyncio
async def check_mirrors_async():
    health_status = await mirror_mgr.check_all_mirrors_async()
    return health_status
    
# Save mirror configuration to persist health data between runs
mirror_mgr.save_mirrors()
```

#### BookDiscovery

Combined interface for discovering and downloading books.

```python
from gutenberg_downloader.discovery import BookDiscovery

discovery = BookDiscovery(mirrors_enabled=True)
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
    async with AsyncEpubDownloader(max_concurrency=5, mirrors_enabled=True) as downloader:
        await downloader.download_multiple_epubs([
            ("https://www.gutenberg.org/ebooks/1342.epub", "my_books/book1.epub", 1342),
            ("https://www.gutenberg.org/ebooks/84.epub", "my_books/book2.epub", 84),
            ("https://www.gutenberg.org/ebooks/11.epub", "my_books/book3.epub", 11),
        ])
        
async def resume_interrupted_downloads():
    # Find and resume interrupted downloads
    async with AsyncEpubDownloader(max_concurrency=3, mirrors_enabled=True) as downloader:
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
- All the Project Gutenberg mirror sites that help distribute the content
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