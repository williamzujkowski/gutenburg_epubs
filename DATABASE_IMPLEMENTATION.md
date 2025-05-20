# Database Implementation for Gutenberg EPUB Downloader

## Overview

The Gutenberg EPUB Downloader includes a comprehensive database solution to efficiently handle the large dataset from Project Gutenberg. The implementation includes SQLite database integration with FTS5 full-text search, API caching, mirror site tracking, and enhanced CLI commands for database management.

## Key Components

### 1. Database Module (`database.py`)

A SQLite-based database system that stores:
- **Books table**: Core book metadata (title, language, download count)
- **Authors table**: Author information with many-to-many relationships
- **Subjects table**: Book categories/genres
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
- `--use-db` flag for all commands to use database
- `--db-path` to specify custom database location
- `--use-mirrors` flag to enable mirror site rotation
- `--preferred-mirrors` to specify preferred mirror sites
- Database-aware search and discovery

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

### Using Database and Mirrors for Operations
```bash
# Discover books using database (faster)
gutenberg-downloader discover --use-db --limit 20

# Search with database
gutenberg-downloader search --use-db --author "Jane Austen"

# Download using mirror rotation
gutenberg-downloader download 1342 --use-mirrors

# Download popular books with database and mirrors
gutenberg-downloader download-popular --use-db --use-mirrors --limit 10
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
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    language TEXT,
    download_count INTEGER DEFAULT 0,
    has_epub BOOLEAN DEFAULT 0,
    epub_url TEXT,
    publication_date TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authors with many-to-many relationships
CREATE TABLE authors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    birth_year INTEGER,
    death_year INTEGER
);

-- Book-Author relationships
CREATE TABLE book_authors (
    book_id INTEGER,
    author_id INTEGER,
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Subjects table
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Book-Subject relationships
CREATE TABLE book_subjects (
    book_id INTEGER,
    subject_id INTEGER,
    PRIMARY KEY (book_id, subject_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Full-text search table
CREATE VIRTUAL TABLE book_content USING fts5(
    book_id UNINDEXED,
    title,
    author,
    subject,
    content,
    tokenize = 'porter unicode61'
);

-- Downloads tracking
CREATE TABLE downloads (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL,
    output_path TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'in_progress', 'completed', 'failed')) DEFAULT 'pending',
    file_size INTEGER DEFAULT 0,
    attempt_count INTEGER DEFAULT 0,
    mirror_url TEXT,
    download_start TIMESTAMP,
    download_end TIMESTAMP,
    last_error TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Mirror sites
CREATE TABLE mirrors (
    id INTEGER PRIMARY KEY,
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
    FOREIGN KEY (mirror_id) REFERENCES mirrors(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
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

The algorithm ensures optimal download performance while respecting server resources and user preferences.

## Best Practices

1. **Initial Setup**: Run `db refresh` to populate the database
2. **Regular Updates**: Periodically refresh to get new books
3. **Use Database Flag**: Add `--use-db` for better performance
4. **Enable Mirrors**: Add `--use-mirrors` for faster, more reliable downloads
5. **Monitor Size**: Database file grows with more books
6. **Backup**: Regularly backup `gutenberg_books.db`

## Future Enhancements

1. **Advanced Mirror Analytics**: Collect more detailed statistics on mirror performance
2. **Automatic Mirror Discovery**: Proactively discover new mirrors
3. **Geographic Optimization**: Select mirrors based on geographic proximity
4. **Bandwidth Tracking**: Track bandwidth usage per mirror
5. **Mirror Testing**: Periodic health checks for mirrors
6. **Custom Mirror Plugins**: Allow users to add custom mirror handlers

This database implementation provides a robust foundation for efficiently managing large book catalogs while ensuring optimal download performance through intelligent mirror site selection.