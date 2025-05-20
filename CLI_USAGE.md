# Gutenberg EPUB Downloader CLI Usage

This document provides examples and instructions for using the Gutenberg EPUB Downloader command-line interface.

## Global Options

These options can be used with any command:

```bash
--verbose, -v           # Enable verbose output (shows debug messages)
--quiet, -q             # Suppress non-error output
--no-db                 # Disable database usage (database is used by default)
--db-path PATH          # Custom path to database file (default: gutenberg_books.db)
--no-mirrors            # Disable mirror site rotation (mirrors are used by default)
--preferred-mirrors LIST # Comma-separated list of preferred mirror URLs
```

### Default Optimizations

The tool enables these optimizations by default for the best experience:

- ✅ **Database Usage**: Faster searches and resumable downloads
- ✅ **Mirror Site Rotation**: Avoids rate limits, faster downloads
  - 🔄 **Automatic Mirror Fallback**: Tries multiple mirrors if one returns 404 "Not Found" error
  - 🔄 **Smart Mirror Health Tracking**: Remembers which mirrors work best
- ✅ **Asynchronous Mode**: Parallel downloads for better performance
- ✅ **Resume Capability**: Can continue interrupted downloads
- ✅ **Skip Existing Files**: Won't re-download books you already have

Use the `--no-*` flags to disable any of these features if needed.

## Available Commands

### 1. Filter Download Command

The most powerful command for downloading books with complex filtering options.

```bash
# Download science fiction books (with all optimizations enabled by default)
gutenberg-downloader filter-download --subjects "science fiction" --output ./scifi_books/

# Download multiple books (up to 1000)
gutenberg-downloader filter-download --subjects "science fiction" --limit 1000 --output ./scifi_books/

# Disable mirror site rotation if needed
gutenberg-downloader filter-download --subjects "science fiction" --no-mirrors --output ./scifi_books/

# Download books matching multiple terms
gutenberg-downloader filter-download --terms "space, aliens, future" --match-any --output ./space_books/

# Combine search terms and subjects with language filtering
gutenberg-downloader filter-download --subjects "adventure, pirates" --terms "treasure" --language en --output ./adventure/

# Set minimum download count
gutenberg-downloader filter-download --subjects "philosophy" --min-downloads 100 --limit 20 --output ./philosophy/

# Disable skipping existing files (to replace already downloaded books)
gutenberg-downloader filter-download --subjects "fiction" --no-skip-existing --output ./fiction/

# Use synchronous mode (slower but uses less resources)
gutenberg-downloader filter-download --subjects "poetry" --sync-mode --output ./poetry/

# Disable resume capability (will overwrite partial downloads)
gutenberg-downloader filter-download --subjects "mystery" --no-resume --output ./mystery/

# Force download even if files already exist (useful for testing mirror fallback)
gutenberg-downloader filter-download --subjects "adventure" --force-download --output ./adventure/
```

### 2. Mirror Site Management

Work with mirror sites to distribute downloads and avoid rate limits.

```bash
# Show status of configured mirror sites with health information
gutenberg-downloader mirrors status

# Update mirror list from Project Gutenberg
gutenberg-downloader mirrors update

# Force a health check on all mirrors
gutenberg-downloader mirrors status --check-health

# Specify preferred mirrors for a download
gutenberg-downloader --preferred-mirrors "https://gutenberg.pglaf.org/,https://aleph.pglaf.org/" download 1342

# Disable mirrors for a download if needed
gutenberg-downloader --no-mirrors download 1342
```

Example output from mirror status command:

```
🔄 Mirror Site Status
──────────────────────────────────────────────────────────────────────
📊 Summary:
  Total mirror sites: 8
  Active mirror sites: 8
  Primary mirror: Project Gutenberg Main
  Configuration: /home/user/.gutenberg_downloader/mirrors.json

📋 Mirror Details:
──────────────────────────────────────────────────────────────────────
Name                      Status   Health   Priority Country  Last Check     
──────────────────────────────────────────────────────────────────────
* Project Gutenberg Main  ✅ Active 🟢 1.00   5        US       2023-05-20 10:14
Project Gutenberg PGLAF   ✅ Active 🟢 1.00   4        US       2023-05-20 10:14
Aleph PGLAF               ✅ Active 🟢 1.00   4        US       2023-05-20 10:14
Nabasny                   ✅ Active 🟢 1.00   3        US       2023-05-20 10:14
UK Mirror Service         ✅ Active 🟢 1.00   2        UK       2023-05-20 10:14
Xmission                  ✅ Active 🟢 1.00   2        US       2023-05-20 10:14
University of Waterloo    ✅ Active 🟢 1.00   1        CA       2023-05-20 10:14
University of Minho       ✅ Active 🟡 0.70   1        PT       2023-05-20 10:14
```

This feature helps you understand the health and availability of different mirror sites for more reliable downloads. Mirrors with lower health scores are automatically deprioritized in favor of healthier mirrors.

### 3. Download Commands

Download specific books or popular books.

```bash
# Download a specific book by ID (all optimizations enabled by default)
gutenberg-downloader download 1342 --output ./downloads/

# Download without mirror site support if needed
gutenberg-downloader download 1342 --no-mirrors --output ./downloads/

# Download popular books (async mode and mirrors enabled by default)
gutenberg-downloader download-popular --limit 5 --output ./downloads/

# Download popular books with custom concurrency level
gutenberg-downloader download-popular --limit 20 --concurrency 8 --output ./downloads/

# Download popular books in synchronous mode (slower but uses less resources)
gutenberg-downloader download-popular --limit 10 --sync-mode --output ./downloads/

# Download with all optimizations disabled
gutenberg-downloader --no-db --no-mirrors download-popular --limit 5 --sync-mode --output ./downloads/
```

### 4. Resume Downloads

Resume interrupted downloads.

```bash
# Resume all interrupted downloads (all optimizations enabled by default)
gutenberg-downloader resume --output ./downloads/

# Resume with synchronous processing if needed (slower but uses less resources)
gutenberg-downloader resume --sync-mode --output ./downloads/

# Resume without mirror support if needed
gutenberg-downloader --no-mirrors resume --output ./downloads/

# Show detailed progress when resuming
gutenberg-downloader resume --verbose --output ./downloads/
```

### 5. Discovery and Search

Find books to download.

```bash
# Discover popular books (database and async mode enabled by default)
gutenberg-downloader discover --limit 20

# Discover without database if needed
gutenberg-downloader --no-db discover --limit 20

# Discover in synchronous mode if needed
gutenberg-downloader discover --sync-mode --limit 20

# Search by title (database enabled by default)
gutenberg-downloader search --title "Pride and Prejudice"

# Search by author with limit
gutenberg-downloader search --author "Jane Austen" --limit 5

# Full-text search (database enabled by default)
gutenberg-downloader search --full-text "Sherlock Holmes"

# Search with all optimizations disabled
gutenberg-downloader --no-db search --title "Pride and Prejudice" --sync-mode
```

### 6. Database and Metadata Management

Manage the local book database and book metadata.

```bash
# Show database statistics
gutenberg-downloader db stats

# Clear the database (requires confirmation)
gutenberg-downloader db clear

# Force clear without confirmation
gutenberg-downloader db clear --force

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

### 7. Genre and Subject Filtering

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

The genre system provides standardized classifications based on subjects and bookshelves, making it easier to find related books. Common genres include:

- Fiction
- Science Fiction
- Fantasy
- Mystery/Detective
- Horror
- Romance
- Historical
- Adventure
- Biography/Memoir
- Poetry
- Drama
- Philosophy
- And many more

## Examples for Bulk Downloads

### Download Top 1000 Sci-Fi Books with Mirror Support

```bash
gutenberg-downloader filter-download \
  --subjects "science fiction" \
  --language en \
  --limit 1000 \
  --output ./scifi_books/
```

### Download Classic Literature with Minimum Download Count

```bash
gutenberg-downloader filter-download \
  --subjects "literature, classic" \
  --min-downloads 500 \
  --limit 100 \
  --output ./classics/
```

### Download Books by Multiple Authors

```bash
gutenberg-downloader filter-download \
  --terms "Shakespeare, Dickens, Austen" \
  --match-any \
  --limit 50 \
  --output ./authors/
```

### 8. Terminal User Interface (TUI)

Interactive terminal interface for browsing, searching, and downloading books.

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

The TUI provides a rich interactive experience with:

- **Browse Tab**: Search and select books to download
- **Downloads Tab**: Track real-time download progress, manage queue
- **Mirrors Tab**: Monitor and manage mirror sites
- **Settings Tab**: Configure application settings

## Best Practices

1. Consider using the TUI (Terminal User Interface) with `--tui` for an interactive experience with real-time progress tracking
2. Enjoy the optimized defaults - database, mirrors, async mode, resume, and skip-existing are all enabled by default
3. Keep mirrors enabled to benefit from automatic 404 error handling and mirror fallback
4. For very large downloads, consider increasing concurrency with `--concurrency 8` (or higher if you have a fast connection)
5. Set a reasonable `--limit` to manage download size
6. Use `--verbose` when troubleshooting issues
7. In case of low resources or slow networks, use `--sync-mode` to reduce resource usage
8. Use `--no-*` flags selectively - the default settings are optimized for most cases
9. If you're experiencing 404 errors, don't worry - the automatic mirror fallback will try multiple mirrors until the book is found
10. Use the TUI's mirror management tab to monitor mirror health and optimize download performance