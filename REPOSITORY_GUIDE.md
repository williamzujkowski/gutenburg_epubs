# Project Gutenberg EPUB Downloader - Repository Guide

This document provides a comprehensive overview of all files and modules in the repository, their purposes, and key functionality. It serves as a central reference for understanding the codebase structure.

## Core Modules

### Main Package: `/src/gutenberg_downloader/`

#### `__init__.py`
- Contains package version and initialization
- Exports public API for the package

#### `__main__.py`
- Entry point for running the package directly
- Passes arguments to CLI module

#### `api_client.py`
- HTTP client for Project Gutenberg API
- Key functions:
  - `get_book_details()` - Fetches metadata for a book
  - `get_popular_books()` - Fetches list of popular books
  - `search_books()` - Searches books by criteria

#### `api_discovery.py`
- Uses API for book discovery
- Key functions:
  - `discover_popular_english_epubs()` - Finds popular English books
  - `search_by_title()` - Searches books by title
  - `search_by_author()` - Searches books by author

#### `api_discovery_db.py`
- Database-backed version of API discovery
- Uses local database cache for faster queries
- Key function: `discover_popular_english_epubs()` with DB support

#### `async_api_client.py`
- Asynchronous version of API client
- Uses `httpx.AsyncClient` for concurrent API requests
- Key functions:
  - `get_book_details_async()` - Asynchronous book metadata fetching
  - `search_books_async()` - Asynchronous book search

#### `async_api_discovery.py`
- Asynchronous version of API discovery
- Enables concurrent discovery operations
- Key function: `discover_popular_english_epubs_async()`

#### `async_discovery.py`
- General asynchronous discovery operations
- Combines scraping with API access where needed
- Key function: `discover_books_async()`

#### `async_epub_downloader.py`
- Asynchronous EPUB downloader
- Allows concurrent downloads with rate limiting
- Key functions:
  - `download_multiple_epubs_async()` - Downloads multiple books concurrently
  - `resume_incomplete_downloads()` - Resumes interrupted downloads

#### `benchmark.py`
- Performance benchmarking tools
- Compares sync vs. async operations
- Key function: `run_benchmark()` - Runs performance tests

#### `cache.py`
- Multi-tier caching system
- Caches API responses and search results
- Key classes:
  - `MemoryCache` - In-memory cache
  - `DiskCache` - Persistent disk-based cache

#### `catalog_importer.py`
- Imports catalog data from CSV and RDF sources
- Populates database with book metadata
- Key function: `import_catalog()` - Imports catalog data

#### `cli.py`
- Main command-line interface
- Handles all CLI arguments and subcommands
- Key functions:
  - `main()` - Entry point for CLI
  - Various command handlers (e.g., `download_command()`, `search_command()`)
  - `mirror_update_command()` - Updates mirror list from Project Gutenberg

#### `config.py`
- Configuration management
- Handles YAML/TOML configuration files
- Key function: `load_config()` - Loads config from files

#### `constants.py`
- Central repository for constants
- Defines URLs, timeouts, retry policies, etc.
- Used throughout the codebase for consistency

#### `database.py`
- SQLite database management
- Full-text search capabilities
- Key class: `BookDatabase` - Core database operations

#### `discovery.py`
- Core book discovery functionality
- Combines various discovery methods
- Key class: `BookDiscovery` - High-level discovery operations

#### `download_queue.py`
- Download queue management
- Prioritizes and schedules downloads
- Key class: `DownloadQueue` - Manages download queue

#### `enhanced_cli.py`
- Enhanced CLI with additional features
- Supplements main CLI functionality
- Used for advanced operations

#### `enhanced_downloader.py`
- Advanced downloader with filtering
- Multi-filter search capabilities
- Key class: `EnhancedDownloader` - Advanced download capabilities
- Key function: `search_and_download()` - Filtered search and download

#### `epub_downloader.py`
- Core EPUB download functionality
- Handles download, resume, and verification
- Key class: `EpubDownloader` - Base downloader implementation

#### `exporter.py`
- Exports data to various formats
- Supports CSV, JSON, Excel, Markdown
- Key function: `export_books()` - Exports book data

#### `logger.py`
- Logging configuration
- Sets up consistent logging throughout the app
- Key function: `setup_logger()` - Configures logging

#### `migrations.py`
- Database migration management
- Handles schema upgrades
- Key function: `migrate_database()` - Upgrades database schema

#### `mirror_manager.py`
- Mirror site management
- Handles mirror rotation, health tracking, and selection
- Key class: `MirrorManager` - Core mirror site functionality
- Key functions:
  - `select_mirror()` - Selects optimal mirror using weighted algorithm
  - `check_mirror_health()` - Checks mirror site health
  - `build_book_url()` - Builds book URL for specific mirror
  - `check_all_mirrors_async()` - Async health check for all mirrors

#### `scraper.py`
- Web scraper for Project Gutenberg
- Extracts book information from HTML
- Key class: `GutenbergScraper` - Scrapes book information

#### `signal_handler.py`
- Handles OS signals
- Ensures clean shutdown
- Key function: `setup_signal_handlers()` - Sets up signal handlers

#### `smart_downloader.py`
- Smart download with resume capability
- Tracks download state and handles failures
- Key class: `SmartDownloader` - Core smart download functionality
- Key functions:
  - `download_with_resume()` - Downloads with resume capability
  - `verify_downloads()` - Verifies download integrity

#### `tui.py`
- Terminal user interface components
- Provides interactive UI elements
- Key class: `TUI` - Terminal UI implementation

## Scripts

### Root Directory Scripts

#### `benchmark_runner.py`
- Runs performance benchmarks
- Compares sync vs. async operations
- Saves results to benchmark_results.md

#### `bulk_download.py`
- Downloads books in bulk
- Uses configuration for bulk operations

#### `debug_formats.py`
- Debugs format detection
- Tests format handling

#### `debug_scraper.py`
- Debugs web scraper
- Tests HTML parsing

#### `debug_search.py`
- Debugs search functionality
- Tests search algorithms

#### `debug_subject.py`
- Debugs subject handling
- Tests subject filtering

#### `download_scifi.py`
- Downloads science fiction books
- Basic example script

#### `download_scifi_mirrors.py`
- Downloads science fiction books using mirrors
- Demonstrates mirror functionality

#### `filter_cli_test.py`
- Tests CLI filtering capabilities
- Verifies filter command works correctly

#### `run_discovery_first.py`
- Runs discovery before other operations
- Sets up initial database

#### `test_alias.py`
- Tests alias functionality
- Verifies command aliases work

#### `test_gutenberg_cli.py`
- Tests CLI functionality
- Verifies commands work as expected

#### `test_mirror_fixes.py`
- Tests mirror functionality fixes
- Verifies mirror selection and health tracking

#### `test_mirror_rotation.py`
- Tests mirror rotation during downloads
- Verifies mirrors rotate properly

#### `update_cli_tests.py`
- Updates CLI tests
- Regenerates test fixtures

#### `use_catalog_importer.py`
- Demonstrates catalog importer
- Imports catalog data into database

#### `validate_scifi_downloads.py`
- Validates downloaded science fiction books
- Checks file integrity

## Test Modules

### `/tests/`

#### `__init__.py`
- Test package initialization

#### `test_api_client.py`
- Tests API client functionality
- Verifies API requests and parsing

#### `test_async_discovery.py`
- Tests async discovery
- Verifies concurrent discovery operations

#### `test_async_epub_downloader.py`
- Tests async downloader
- Verifies concurrent downloads

#### `test_cache.py`
- Tests caching system
- Verifies cache operations

#### `test_cli.py`
- Tests CLI functionality
- Verifies command parsing and execution

#### `test_database.py`
- Tests database operations
- Verifies schema and queries

#### `test_discovery.py`
- Tests discovery functionality
- Verifies book discovery

#### `test_epub_downloader.py`
- Tests EPUB downloader
- Verifies download operations

#### `test_logger.py`
- Tests logging configuration
- Verifies log output

#### `test_scraper.py`
- Tests web scraper
- Verifies HTML parsing

## Documentation

### Root Documentation

#### `BULK_DOWNLOAD_INSTRUCTIONS.md`
- Instructions for bulk downloads
- Configuration options for bulk operations

#### `CHANGELOG.md`
- Version history
- Changes by version

#### `CLI_USAGE.md`
- CLI usage documentation
- Command examples and options

#### `CONTRIBUTING.md`
- Contribution guidelines
- How to contribute to the project

#### `DATABASE_IMPLEMENTATION.md`
- Database schema and usage
- How the database is structured

#### `DOWNLOAD_SUCCESS.md`
- How to verify successful downloads
- Integrity checking

#### `DOWNLOAD_SUMMARY.md`
- Summary of download statistics
- Performance metrics

#### `FINAL_REPORT.md`
- Project final report
- Overall project summary

#### `PROJECT_STATUS.md`
- Current project status
- Completed and planned phases

#### `README.md`
- Project overview
- Installation and usage instructions

#### `REPOSITORY_GUIDE.md`
- This file
- Central documentation of repository structure

#### `RUFF_MIGRATION.md`
- Migration to ruff linter
- How to update code for ruff

## Configuration

### `/examples/`

#### `config.toml`
- Example TOML configuration
- Shows all available options

#### `config.yaml`
- Example YAML configuration
- Shows all available options

#### `benchmark_results.md`
- Results of performance benchmarks
- Comparison of different modes

## Directory Structure

- `/src/gutenberg_downloader/` - Main package source code
- `/tests/` - Test modules
- `/examples/` - Example configurations
- `/downloads/` - Default download directory
- `/bulk_downloads/` - Directory for bulk downloads
- `/scifi_books/` - Directory for science fiction books
- `/htmlcov/` - Test coverage reports
- `/test_downloads/` - Test download directory
- `/.llmconfig/` - Configuration for LLM integration

## Key Interfaces

### Download Interface

Core classes that implement download functionality:

1. `EpubDownloader` - Base downloader
2. `AsyncEpubDownloader` - Concurrent downloader
3. `SmartDownloader` - Resumable downloader
4. `EnhancedDownloader` - Advanced filtering downloader

### Discovery Interface

Core classes that implement discovery functionality:

1. `BookDiscovery` - Base discovery
2. `AsyncBookDiscovery` - Concurrent discovery
3. `APIBookDiscovery` - API-based discovery
4. `APIBookDiscoveryDB` - Database-backed discovery

### Mirror Interface

Functionality to handle mirror site rotation:

1. `MirrorManager` - Manages mirror selection
2. `MirrorSite` - Represents a mirror site

### Database Interface

Database functionality:

1. `BookDatabase` - Core database operations
2. Migration functions in `migrations.py`

## Functionality Map

### Book Discovery:
- `discovery.py` -> Basic discovery
- `api_discovery.py` -> API-based discovery
- `async_discovery.py` -> Async discovery
- `scraper.py` -> HTML scraping
- `api_discovery_db.py` -> DB-backed discovery

### Downloading:
- `epub_downloader.py` -> Base download
- `async_epub_downloader.py` -> Async download
- `smart_downloader.py` -> Resumable download
- `enhanced_downloader.py` -> Advanced download
- `download_queue.py` -> Queue management

### Mirror Sites:
- `mirror_manager.py` -> Mirror management
- Mirror commands in `cli.py`

### User Interface:
- `cli.py` -> Command-line interface
- `enhanced_cli.py` -> Enhanced CLI
- `tui.py` -> Terminal UI components

### Data Storage:
- `database.py` -> SQLite database
- `cache.py` -> Cache system
- `exporter.py` -> Data export

## Key Architecture Features

1. **Modular Design**:
   - Clear separation of concerns
   - Pluggable components

2. **Progressive Enhancement**:
   - Base functionality first
   - Advanced features layered on top

3. **Multiple Operation Modes**:
   - Synchronous for simplicity
   - Asynchronous for performance
   - Database-backed for scalability

4. **Resilient Operation**:
   - Comprehensive error handling
   - Resume capabilities
   - Mirror rotation for reliability

5. **Configurable Behavior**:
   - YAML/TOML configuration
   - Command-line options
   - Sensible defaults

## Development Guidelines

1. **Adding New Features**:
   - Implement in dedicated module
   - Add tests in `/tests/`
   - Update CLI in `cli.py`
   - Update documentation in README.md

2. **Bug Fixes**:
   - Include test case that reproduces issue
   - Update relevant documentation
   - Add to CHANGELOG.md

3. **Performance Improvements**:
   - Measure with `benchmark.py`
   - Document improvements in benchmark_results.md