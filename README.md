# Gutenberg EPUB Downloader

[![CI](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/ci.yml/badge.svg)](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/ci.yml)
[![CodeQL](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/codeql.yml/badge.svg)](https://github.com/williamzujkowski/gutenburg_epubs/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A Python tool for discovering and downloading EPUB books from Project Gutenberg, featuring both synchronous and asynchronous capabilities, comprehensive database management, and a user-friendly command-line interface with optimized defaults for the best experience.

> **Optimized for Best Experience:** All commands now use intelligent defaults (database, mirror rotation, async mode, resume capability) - just run the commands and enjoy the benefits without needing to specify extra flags!

## Latest Updates

- ✅ Added comprehensive metadata extraction with standardized genre classification
- ✅ Enhanced database schema to store bookshelves, subjects, and genre relationships
- ✅ Added metadata refresh command for updating book information from multiple sources
- ✅ Implemented intelligent genre detection from subjects and bookshelves
- ✅ Added Library of Congress Classification (LCC) support for better categorization
- ✅ Added Terminal User Interface (TUI) with real-time download progress tracking
- ✅ Added interactive mirror management with health visualization
- ✅ Added download queue management with parallel download tracking
- ✅ Added intelligent 404 error handling that automatically tries multiple mirrors until a book is found
- ✅ Optimized defaults for superior out-of-box experience (all optimizations enabled by default)
- ✅ Enhanced mirror site support with persistent health tracking and automatic updates
- ✅ Improved mirror selection algorithm with weighted health-based selection
- ✅ Added multi-filter download capability for combining search terms and subjects
- ✅ Fixed database integration with proper full-text search support
- ✅ Improved download reliability with robust streaming and resume capabilities
- ✅ Enhanced download speed with concurrent and asynchronous downloads
- ✅ Added smart download system that tracks progress and can resume interrupted downloads
- ✅ Implemented comprehensive catalog import from both CSV and RDF sources
- ✅ Simplified CLI interface with intelligent defaults and clear documentation

## Features

- 🔍 **Discovery**: Find popular English books with EPUB files from Project Gutenberg
- 📊 **Database**: SQLite storage with FTS5 full-text search capability
- 🔎 **Advanced Search**: Look up books by title, author, subject, or full-text
- 🧠 **Multi-filter Search**: Combine search terms and subject filters
- 📝 **Metadata**: Comprehensive metadata extraction with standardized genre classification
- 📚 **Genre System**: Intelligent genre detection from subjects and bookshelves
- 🏷️ **Classifications**: Library of Congress Classification (LCC) support
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
- 🔃 **Metadata Refresh**: Update book information from multiple sources (API, CSV, RDF)

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
# Discover popular books (database enabled by default)
gutenberg-downloader discover --limit 20

# Explicitly disable database if needed
gutenberg-downloader --no-db discover --limit 20
```

### Searching for Books

```bash
# Search by title (database enabled by default)
gutenberg-downloader search --title "Pride and Prejudice"

# Search by author
gutenberg-downloader search --author "Jane Austen" --limit 5

# Full-text search (requires database, which is on by default)
gutenberg-downloader search --full-text "Sherlock Holmes"

# Search without using the database
gutenberg-downloader --no-db search --author "Mark Twain"
```

### Downloading Books

```bash
# Download a specific book by ID (mirrors and database enabled by default)
gutenberg-downloader download 1342 --output ./downloads/

# Download without using mirror sites
gutenberg-downloader --no-mirrors download 1342 --output ./downloads/

# Download popular books
gutenberg-downloader download-popular --limit 5 --output ./downloads/

# Download with synchronous mode (slower but uses less resources)
gutenberg-downloader download-popular --limit 10 --sync-mode --output ./downloads/

# Set concurrency level for downloads (async is default)
gutenberg-downloader download-popular --limit 20 --concurrency 8 --output ./downloads/

# Disable all optimizations if needed
gutenberg-downloader --no-db --no-mirrors download-popular --limit 5 --sync-mode --output ./downloads/
```

### Multi-Filter Downloading

The `filter-download` command allows you to combine multiple search terms and filters:

```bash
# Download science fiction books (with all optimizations enabled by default)
gutenberg-downloader filter-download --subjects "science fiction" --output ./scifi/

# Download books matching multiple keywords
gutenberg-downloader filter-download --terms "space, aliens, future" --match-any --output ./space/

# Combine search terms and subjects with language filtering
gutenberg-downloader filter-download --subjects "adventure, pirates" --terms "treasure" --language en --output ./adventure/

# Set minimum download count and limit results
gutenberg-downloader filter-download --subjects "philosophy" --min-downloads 100 --limit 20 --output ./philosophy/

# Download without skipping existing files (to replace them)
gutenberg-downloader filter-download --subjects "science fiction" --no-skip-existing --output ./scifi/
```

### Using Mirror Sites for Better Downloads

```bash
# Mirror site rotation is enabled by default for all commands
gutenberg-downloader download-popular --limit 10 --output ./downloads/

# Disable mirror rotation if needed
gutenberg-downloader --no-mirrors download-popular --limit 10 --output ./downloads/

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
metadata              - Update/refresh metadata for books in the database
```

Global options available for most commands:
```
--verbose, -v         - Enable verbose output
--quiet, -q           - Suppress non-error output
--no-db               - Disable database usage (database is used by default)
--db-path             - Path to database file (default: gutenberg_books.db)
--no-mirrors          - Disable mirror site rotation (mirrors are used by default)
--preferred-mirrors   - Comma-separated list of preferred mirror URLs
```

Default optimizations enabled:
- Database usage (faster searches and resumable downloads)
- Mirror site rotation (avoids rate limits, faster downloads)
- Asynchronous mode (parallel downloads for better performance)
- Resume capability (can continue interrupted downloads)
- Skip existing files (won't re-download books you already have)
- Metadata extraction (comprehensive book information)
- Genre classification (standardized categorization of books)

Use the `--no-*` flags to disable any of these features if needed.

### Database Management

```bash
# Get database statistics
gutenberg-downloader db stats

# Clear database (with confirmation prompt)
gutenberg-downloader db clear

# Force clear database without confirmation
gutenberg-downloader db clear --force
```

### Metadata Management

```bash
# Refresh metadata for all books in the database
gutenberg-downloader metadata --refresh

# Refresh metadata for books in a specific directory
gutenberg-downloader metadata --sync-dir ./downloads/

# Force refresh metadata even for up-to-date books
gutenberg-downloader metadata --refresh --force

# Refresh metadata from a specific source (api, csv, rdf, or all)
gutenberg-downloader metadata --refresh --source rdf

# Limit the number of books to refresh metadata for
gutenberg-downloader metadata --refresh --limit 100

# Or use the simplified command with the output directory
gutenberg-downloader --refresh-metadata --output ./downloads/ --verbose
```

### Genre and Subject Filtering

Filter and discover books by genre, subject, and bookshelf categories:

```bash
# Download science fiction books
gutenberg-downloader filter-download --subjects "science fiction" --output ./scifi_books/

# Download books from multiple genres
gutenberg-downloader filter-download --subjects "mystery, detective" --output ./mystery_books/

# Combine subject search with additional search terms
gutenberg-downloader filter-download --subjects "adventure" --terms "ocean, sea" --output ./sea_adventure/

# Filter by genre with minimum popularity
gutenberg-downloader filter-download --subjects "fantasy" --min-downloads 100 --output ./fantasy/

# Search for books by subject with the TUI
gutenberg-downloader filter-download --tui --subject "historical"
```

### Resume Interrupted Downloads

```bash
# Resume all interrupted downloads (with all optimizations enabled by default)
gutenberg-downloader resume --output ./downloads/

# Resume with synchronous processing (slower but uses less resources)
gutenberg-downloader resume --output ./downloads/ --sync-mode

# Resume without mirror site rotation if needed
gutenberg-downloader --no-mirrors resume --output ./downloads/

# Show detailed progress when resuming
gutenberg-downloader resume --output ./downloads/ --verbose
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

The Gutenberg EPUB Downloader includes robust support for mirror sites to:

1. **Distribute Load**: Avoid hitting rate limits from a single server by rotating between mirrors
2. **Improve Speed**: Select faster mirrors based on response time and health
3. **Increase Reliability**: Continue working even if some mirrors are down
4. **Maximize Availability**: Find books that may be missing on some mirrors but available on others

### How Mirror Selection Works

The system intelligently selects the best mirror for each download based on:

1. **Health Score**: Each mirror gets a health score based on response time and reliability
2. **Priority**: Some mirrors are prioritized over others (can be customized)
3. **Recent Usage**: The system avoids using the same mirror repeatedly in a short timeframe
4. **Book Availability**: Only mirrors known to have the specific book are selected
5. **User Preferences**: You can specify preferred mirrors and countries in the configuration
6. **Failure History**: Mirrors with repeated failures have lower selection probability

### Mirror Site Capabilities

- **Automatic Rotation**: Seamlessly switch between mirrors if one fails
- **Health Tracking**: Continuously monitor mirror health and adjust preferences with persistent health data
- **Failed Request Handling**: Automatically retry with a different mirror if a download fails
- **Smart 404 Error Handling**: When a mirror returns a 404 (Not Found) error, automatically tries additional mirrors until the book is found
  - *All Project Gutenberg mirrors have slightly different file structures and book availability*
  - *The system will keep trying different mirrors when a 404 occurs, maximizing download success rates*
  - *Mirrors that consistently return 404s have their health scores reduced automatically*
  - *This happens transparently to the user - no additional configuration needed*
- **Country-Based Selection**: Prefer mirrors in specific countries for better performance
- **Weighted Selection**: Intelligent mirror choice based on health score, priority, and recent usage
- **Auto-Discovery**: Update mirror list from Project Gutenberg's MIRRORS.ALL file
- **Health Persistence**: Mirror health data is saved between runs in user's home directory
- **Configuration Options**: Extensive customization through YAML config
- **URL Structure Adaptation**: Automatically adapts to different mirror site URL structures
- **Asynchronous Health Checks**: Efficiently test multiple mirrors concurrently
- **Progressive Health Scoring**: Mirrors gradually recover health after successful operations

### Programming with the API

```python
from gutenberg_downloader import EpubDownloader, MirrorManager

# Use the mirror manager directly (mirrors enabled by default)
mirror_mgr = MirrorManager()
book_url = mirror_mgr.get_book_url(book_id=1342)

# Create a downloader with default optimizations
downloader = EpubDownloader()  # mirrors_enabled=True by default
success = downloader.download_epub(
    url="https://www.gutenberg.org/ebooks/1342.epub",
    output_path="downloads/pride_and_prejudice.epub",
    book_id=1342,  # For mirror selection
    resume=True    # Resume capability enabled by default
)

# Disable optimizations if needed
downloader_basic = EpubDownloader(mirrors_enabled=False)
success = downloader_basic.download_epub(
    url="https://www.gutenberg.org/ebooks/1342.epub",
    output_path="downloads/pride_and_prejudice.epub",
    resume=False
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
# (all optimizations enabled by default: database, mirrors, async, resume)
gutenberg-downloader resume --output ~/books

# Resume with synchronous mode if needed (slower but uses less resources)
gutenberg-downloader resume --output ~/books --sync-mode

# Without database integration (not recommended, slower matching)
gutenberg-downloader --no-db resume --output ~/books

# Without mirror site rotation if needed
gutenberg-downloader --no-mirrors resume --output ~/books

# Show detailed progress
gutenberg-downloader resume --output ~/books --verbose
```

### Resume During Regular Downloads

Resume capability is enabled by default for all download operations. You can disable it if needed:

```bash
# Download a book with resume capability (enabled by default)
gutenberg-downloader download 1342 --output ~/books/

# Disable resume capability if needed (will overwrite partial files)
gutenberg-downloader filter-download --subjects "science fiction" --no-resume --output ~/books/

# Resume capability works with all download commands automatically
gutenberg-downloader download-popular --limit 10 --output ~/books/
```

## Terminal User Interface (TUI)

The Gutenberg EPUB Downloader now includes a comprehensive Terminal User Interface for a more interactive and visual experience. The TUI provides real-time download progress tracking, interactive book browsing, mirror management, and more.

### Launching the TUI

```bash
# Launch the TUI with default settings
gutenberg-downloader filter-download --tui

# Launch with custom database path
gutenberg-downloader filter-download --tui --db-path custom_books.db

# Launch with custom output directory
gutenberg-downloader filter-download --tui --output ~/my_books

# Launch with custom worker count
gutenberg-downloader filter-download --tui --max-workers 5

# Launch without mirrors if needed
gutenberg-downloader filter-download --tui --no-mirrors
```

### TUI Features

The TUI includes multiple tabs with different functionality:

1. **Browse Tab**
   - Browse and search for books
   - Select books to download
   - View book details including title, author, language, and popularity

2. **Downloads Tab**
   - Real-time download progress visualization
   - Manage active downloads
   - View pending and completed downloads
   - Resume interrupted downloads
   - Clear completed downloads

3. **Mirrors Tab**
   - View all available mirror sites
   - Monitor mirror health and status
   - Test individual mirrors
   - Toggle mirror active state
   - Save mirror configuration

4. **Settings Tab**
   - Configure database path
   - Set output directory
   - Toggle mirror usage
   - Adjust worker count for concurrent downloads
   - Control other download behavior

### Keyboard Shortcuts

The TUI supports various keyboard shortcuts for quick navigation:

- **q**: Quit application
- **s**: Search for books
- **d**: Download selected books
- **e**: Export current view to file (CSV, JSON, Excel, Markdown)
- **r**: Refresh book list
- **?**: Show help
- **Tab**: Switch between tabs
- **Shift+Tab**: Switch to previous tab

### Navigation

- Use **Tab** and **Shift+Tab** to navigate between tabs
- Click on table rows to select books for download
- Use buttons for common operations
- Press **?** at any time to see help

### Programmatic Usage

```python
# Synchronous resume
from gutenberg_downloader.epub_downloader import EpubDownloader

# Create a downloader with optimal defaults
downloader = EpubDownloader()  # mirrors_enabled=True by default
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
    async with AsyncEpubDownloader(max_concurrency=5) as downloader:  # mirrors enabled by default
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
    async with AsyncEpubDownloader(max_concurrency=5) as downloader:  # mirrors enabled by default
        await downloader.download_multiple_epubs([
            ("https://www.gutenberg.org/ebooks/1342.epub", "my_books/book1.epub", 1342),
            ("https://www.gutenberg.org/ebooks/84.epub", "my_books/book2.epub", 84),
            ("https://www.gutenberg.org/ebooks/11.epub", "my_books/book3.epub", 11),
        ])
        
async def resume_interrupted_downloads():
    # Find and resume interrupted downloads
    async with AsyncEpubDownloader(max_concurrency=3) as downloader:  # mirrors enabled by default
        # Find partial downloads
        incomplete_files = await downloader.find_incomplete_downloads("my_books")
        
        # Create URL mapping (example)
        url_mapping = {
            file_path: f"https://www.gutenberg.org/ebooks/{book_id}.epub"
            for file_path, book_id in file_to_id_mapping.items()
        }
        
        # Resume all interrupted downloads (resume enabled by default)
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