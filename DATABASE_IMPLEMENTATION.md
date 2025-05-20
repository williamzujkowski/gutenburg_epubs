# Database Implementation for Gutenberg EPUB Downloader

## Overview

The Gutenberg EPUB Downloader includes a comprehensive database solution to efficiently handle the large dataset from Project Gutenberg. The implementation includes SQLite database integration with FTS5 full-text search, API caching, mirror site tracking, and enhanced CLI commands for database management.

## Key Components

### 1. Database Module (`database.py`)

A SQLite-based database system that stores:
- **Books table**: Core book metadata (title, language, download count)
- **Authors table**: Author information with many-to-many relationships
- **Subjects table**: Book categories from Project Gutenberg
- **Bookshelves table**: Project Gutenberg bookshelf categories
- **Genres table**: Standardized genre classifications derived from subjects and bookshelves
- **Formats table**: Available download formats for each book  
- **Downloads table**: Track downloaded books and file locations
- **Mirrors table**: Information about mirror sites
- **MirrorBookAvailability table**: Track which books are available on which mirrors

Key features:
- Efficient indexing for fast queries
- FTS5 integration for full-text search
- JSON storage for flexible metadata
- Transaction support for bulk operations
- Comprehensive search functionality
- Mirror site health tracking

### 2. Cache Module (`cache.py`)

Two-tier caching system:
- **API Cache**: File-based cache for API responses (24-hour TTL)
- **In-Memory Cache**: Fast access for frequently used data (5-minute TTL)

Benefits:
- Reduces API calls significantly
- Faster response times for repeated queries
- Configurable cache expiration
- Avoids hitting rate limits from Project Gutenberg and its mirrors

### 3. Mirror Manager Integration (`mirror_manager.py`)

The database is integrated with the mirror manager to:
- Store information about mirror sites
- Track health and availability of mirrors
- Record which books are available on which mirrors
- Provide statistics on mirror performance
- Support intelligent mirror selection based on historical performance

### 4. Enhanced API Client

Updated `api_client.py` with:
- Automatic response caching
- Cache key generation from request parameters
- Transparent cache integration
- Mirror site support

### 5. Database-Integrated Discovery (`api_discovery_db.py`)

Discovery module that:
- Checks database before making API calls
- Automatically stores API results in database
- Falls back to database if API is unavailable
- Tracks download history
- Records mirror availability and performance

### 6. CLI Enhancements

Enhanced database commands:
- `gutenberg-downloader db refresh --limit 1000`: Populate database from API
- `gutenberg-downloader db stats`: Show database statistics
- `gutenberg-downloader db clear`: Clear the database
- `gutenberg-downloader mirrors status`: Show mirror site status
- `gutenberg-downloader mirrors update`: Update mirror list from Project Gutenberg

Enhanced existing commands:
- Database usage enabled by default (use `--no-db` to disable)
- `--db-path` to specify custom database location
- Mirror rotation enabled by default (use `--no-mirrors` to disable)
- `--preferred-mirrors` to specify preferred mirror sites
- Database-aware search and discovery
- Asynchronous mode enabled by default (use `--sync-mode` to use synchronous mode)
- Resume capability enabled by default (use `--no-resume` to disable)

## Usage Examples

### Initial Database Population
```bash
# Populate database with 1000 popular books
gutenberg-downloader db refresh --limit 1000

# Check database statistics
gutenberg-downloader db stats

# Update mirror site list
gutenberg-downloader mirrors update
```

### Operations with Optimized Defaults
```bash
# Discover books (database and mirrors enabled by default)
gutenberg-downloader discover --limit 20

# Search for books (database enabled by default)
gutenberg-downloader search --author "Jane Austen"

# Download a book (mirrors and resume enabled by default)
gutenberg-downloader download 1342 --output ./books/

# Download popular books (all optimizations enabled by default)
gutenberg-downloader download-popular --limit 10 --output ./books/

# Disable optimizations if needed
gutenberg-downloader --no-db --no-mirrors download-popular --sync-mode --limit 10
```

## Performance Benefits

1. **Reduced API Calls**: Cache and database eliminate redundant API requests
2. **Faster Searches**: SQLite indexes provide sub-second query times
3. **Distributed Load**: Mirror rotation prevents hitting rate limits
4. **Faster Downloads**: Selecting faster mirrors improves download speed
5. **Offline Operation**: Can work with cached data when API is unavailable
6. **Bulk Operations**: Efficient handling of thousands of books
7. **Download Tracking**: Avoid re-downloading books

## Database Schema

```sql
-- Books table with core metadata
CREATE TABLE books (
    book_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    language TEXT,
    download_count INTEGER,
    copyright_status BOOLEAN,
    media_type TEXT,
    metadata JSON,
    full_metadata JSON,
    metadata_version INTEGER DEFAULT 1,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id)
);

-- Authors with many-to-many relationships
CREATE TABLE authors (
    author_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    birth_year INTEGER,
    death_year INTEGER,
    UNIQUE(name)
);

-- Book-Author relationships
CREATE TABLE book_authors (
    book_id INTEGER,
    author_id INTEGER,
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    FOREIGN KEY (author_id) REFERENCES authors(author_id)
);

-- Subjects table
CREATE TABLE subjects (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    UNIQUE(name)
);

-- Book-Subject relationships
CREATE TABLE book_subjects (
    book_id INTEGER,
    subject_id INTEGER,
    PRIMARY KEY (book_id, subject_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

-- Bookshelves table (Project Gutenberg categorizations)
CREATE TABLE bookshelves (
    bookshelf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    UNIQUE(name)
);

-- Book-Bookshelf relationships
CREATE TABLE book_bookshelves (
    book_id INTEGER,
    bookshelf_id INTEGER,
    PRIMARY KEY (book_id, bookshelf_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    FOREIGN KEY (bookshelf_id) REFERENCES bookshelves(bookshelf_id)
);

-- Genres table (standardized classifications)
CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_genre_id INTEGER,
    UNIQUE(name),
    FOREIGN KEY (parent_genre_id) REFERENCES genres(genre_id)
);

-- Book-Genre relationships
CREATE TABLE book_genres (
    book_id INTEGER,
    genre_id INTEGER,
    confidence REAL DEFAULT 1.0,  -- How confident we are in this genre classification (0.0-1.0)
    source TEXT,  -- Where this genre classification came from (e.g., 'api', 'bookshelf', 'subject')
    PRIMARY KEY (book_id, genre_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
);

-- Formats table (available download formats)
CREATE TABLE formats (
    format_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    format_type TEXT NOT NULL,
    url TEXT NOT NULL,
    mime_type TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

-- Downloads tracking
CREATE TABLE downloads (
    download_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    download_path TEXT NOT NULL,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bytes_downloaded INTEGER DEFAULT 0,
    total_bytes INTEGER DEFAULT 0,
    status TEXT CHECK(status IN ('pending', 'downloading', 'completed', 'failed')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    UNIQUE(book_id, download_path)
);

-- Full-text search for books
CREATE VIRTUAL TABLE books_fts USING fts5(
    book_id,
    title,
    author,
    subjects,
    bookshelves,
    genres,
    content='books',
    content_rowid='book_id'
);

-- Full-text search for genres
CREATE VIRTUAL TABLE genres_fts USING fts5(
    genre_id,
    name,
    content='genres',
    content_rowid='genre_id'
);

-- Mirror sites
CREATE TABLE mirrors (
    mirror_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    base_url TEXT UNIQUE NOT NULL,
    country TEXT,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    health_score REAL DEFAULT 1.0,
    failure_count INTEGER DEFAULT 0,
    last_checked TIMESTAMP,
    last_error TEXT,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mirror book availability tracking
CREATE TABLE mirror_book_availability (
    mirror_id INTEGER,
    book_id INTEGER,
    verified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (mirror_id, book_id),
    FOREIGN KEY (mirror_id) REFERENCES mirrors(mirror_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
);

-- Download statistics
CREATE TABLE download_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_duration_ms INTEGER,
    file_size_bytes INTEGER,
    success BOOLEAN,
    error_message TEXT,
    source TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

-- Session statistics
CREATE TABLE session_stats (
    session_id TEXT PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    total_downloads INTEGER DEFAULT 0,
    successful_downloads INTEGER DEFAULT 0,
    failed_downloads INTEGER DEFAULT 0,
    total_bytes_downloaded INTEGER DEFAULT 0,
    avg_download_speed_bps REAL
);

-- Cache table
CREATE TABLE cache (
    cache_key TEXT PRIMARY KEY,
    data BLOB,
    content_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata TEXT
);
```

## Mirror Site Selection Algorithm

The database plays a crucial role in the mirror site selection algorithm:

1. **Initial Selection**: The system queries the mirrors table for active mirrors with good health scores
2. **Health Score Calculation**: Health scores are calculated based on:
   - Successful downloads (increases score)
   - Failed downloads (decreases score)
   - Response time
   - Historical reliability
3. **Book Availability**: The system checks the mirror_book_availability table to prioritize mirrors known to have the specific book
4. **Weighted Random Selection**: Mirrors are selected using a weighted random algorithm that factors in:
   - Mirror priority (configurable)
   - Health score
   - Recent usage (to avoid overloading a single mirror)
   - User preferences (preferred mirrors and countries)
5. **Failure Handling**: If a download fails, the mirror's health score is decreased and another mirror is tried
6. **404 Error Smart Handling**: When a mirror returns a 404 Not Found error:
   - The system automatically marks the mirror as not having that book
   - It immediately tries alternative mirrors until the book is found
   - This handling is transparent to the user - no configuration needed
   - Mirrors that consistently return 404s have reduced health scores

The algorithm ensures optimal download performance while respecting server resources and user preferences.

## Best Practices

1. **Initial Setup**: Run `db refresh` to populate the database
2. **Regular Updates**: Periodically refresh to get new books
3. **Use Default Optimizations**: Enjoy the optimized defaults (database, mirrors, async, resume)
4. **Keep Mirrors Enabled**: Leave mirror support enabled to benefit from the 404 error fallback mechanism
5. **Tune Concurrency**: Adjust `--concurrency` value for faster parallel downloads
6. **Monitor Size**: Database file grows with more books
7. **Backup**: Regularly backup `gutenberg_books.db`
8. **Sync Mode**: Use `--sync-mode` for low-resource environments

## Metadata and Genre System

The enhanced database schema includes comprehensive support for book metadata and genre classification:

1. **Multi-source Metadata**: Combines data from multiple sources:
   - Gutendex API (primary source)
   - Project Gutenberg CSV catalog
   - Project Gutenberg RDF catalog

2. **Standardized Genre Classification**: The system automatically extracts and standardizes genres:
   - Analyzes subjects from Project Gutenberg
   - Analyzes bookshelves categorizations
   - Maps both to standardized genre classifications
   - Uses a confidence scoring system for genre assignments
   - Tracks the source of each genre classification

3. **Rich Metadata Storage**:
   - Full book metadata including publication details, copyright information
   - Complete author information with birth/death years
   - Library of Congress Classification (LCC) support
   - Comprehensive subject and bookshelf relationships
   - Full-text search across all metadata fields

4. **Metadata Refresh Capabilities**:
   - Update outdated book information
   - Enhance existing records with more complete data
   - Synchronize data across multiple sources
   - Retain full provenance of information sources
   - Support for metadata versioning

5. **Powerful Genre-Based Discovery**:
   - Search by standardized genre
   - Filter by subject and bookshelf
   - Combine genre filters with other search criteria
   - Full-text search within specific genres
   - Cross-referenced genre relationships

## Future Enhancements

1. **Advanced Mirror Analytics**: Collect more detailed statistics on mirror performance
2. **Automatic Mirror Discovery**: Proactively discover new mirrors
3. **Geographic Optimization**: Select mirrors based on geographic proximity
4. **Bandwidth Tracking**: Track bandwidth usage per mirror
5. **Mirror Testing**: Periodic health checks for mirrors
6. **Custom Mirror Plugins**: Allow users to add custom mirror handlers
7. **Genre Hierarchy**: Implement hierarchical genre relationships (parent/child)
8. **Machine Learning Classification**: Use ML to improve genre classification
9. **Automated Metadata Enhancement**: Proactively fill missing metadata
10. **Cross-referencing**: Link related books based on subjects and genres

This database implementation provides a robust foundation for efficiently managing large book catalogs with rich metadata, powerful genre classification, and optimal download performance through intelligent mirror site selection.