# Gutenberg EPUB Downloader CLI Usage

This document provides examples and instructions for using the Gutenberg EPUB Downloader command-line interface.

## Global Options

These options can be used with any command:

```bash
--verbose, -v           # Enable verbose output (shows debug messages)
--quiet, -q             # Suppress non-error output
--use-db                # Use database for operations (recommended)
--db-path PATH          # Custom path to database file (default: gutenberg_books.db)
--use-mirrors           # Enable mirror site rotation to avoid rate limits
--preferred-mirrors LIST # Comma-separated list of preferred mirror URLs
```

## Available Commands

### 1. Filter Download Command

The most powerful command for downloading books with complex filtering options.

```bash
# Download science fiction books
gutenberg-downloader filter-download --subjects "science fiction" --output ./scifi_books/

# Download multiple books (up to 1000)
gutenberg-downloader filter-download --subjects "science fiction" --limit 1000 --output ./scifi_books/

# Enable mirror site rotation for faster downloads
gutenberg-downloader filter-download --subjects "science fiction" --use-mirrors --output ./scifi_books/

# Download books matching multiple terms
gutenberg-downloader filter-download --terms "space, aliens, future" --match-any --output ./space_books/

# Combine search terms and subjects with language filtering
gutenberg-downloader filter-download --subjects "adventure, pirates" --terms "treasure" --language en --output ./adventure/

# Set minimum download count
gutenberg-downloader filter-download --subjects "philosophy" --min-downloads 100 --limit 20 --output ./philosophy/

# Skip books that already exist in the output directory
gutenberg-downloader filter-download --subjects "fiction" --skip-existing --output ./fiction/
```

### 2. Mirror Site Management

Work with mirror sites to distribute downloads and avoid rate limits.

```bash
# Show status of configured mirror sites
gutenberg-downloader mirrors status

# Update mirror list from Project Gutenberg
gutenberg-downloader mirrors update
```

### 3. Download Commands

Download specific books or popular books.

```bash
# Download a specific book by ID
gutenberg-downloader download 1342 --output ./downloads/

# Download with mirror site support
gutenberg-downloader download 1342 --use-mirrors --output ./downloads/

# Download popular books
gutenberg-downloader download-popular --limit 5 --output ./downloads/

# Download popular books asynchronously with mirror support
gutenberg-downloader download-popular --limit 20 --async-mode --concurrency 5 --use-mirrors --output ./downloads/
```

### 4. Resume Downloads

Resume interrupted downloads.

```bash
# Resume all interrupted downloads in a directory
gutenberg-downloader resume --output ./downloads/

# Resume with mirror support
gutenberg-downloader resume --use-mirrors --output ./downloads/

# Resume with async mode for faster processing
gutenberg-downloader resume --async-mode --output ./downloads/
```

### 5. Discovery and Search

Find books to download.

```bash
# Discover popular books
gutenberg-downloader discover --limit 20

# Discover with database for better performance
gutenberg-downloader discover --use-db --limit 20

# Search by title
gutenberg-downloader search --title "Pride and Prejudice"

# Search by author
gutenberg-downloader search --author "Jane Austen" --limit 5

# Full-text search (requires database)
gutenberg-downloader search --full-text "Sherlock Holmes" --use-db
```

### 6. Database Management

Manage the local book database.

```bash
# Show database statistics
gutenberg-downloader db stats

# Clear the database (requires confirmation)
gutenberg-downloader db clear

# Force clear without confirmation
gutenberg-downloader db clear --force
```

## Examples for Bulk Downloads

### Download Top 1000 Sci-Fi Books with Mirror Support

```bash
gutenberg-downloader filter-download \
  --subjects "science fiction" \
  --language en \
  --limit 1000 \
  --use-mirrors \
  --use-db \
  --skip-existing \
  --output ./scifi_books/
```

### Download Classic Literature with Minimum Download Count

```bash
gutenberg-downloader filter-download \
  --subjects "literature, classic" \
  --min-downloads 500 \
  --limit 100 \
  --use-mirrors \
  --output ./classics/
```

### Download Books by Multiple Authors

```bash
gutenberg-downloader filter-download \
  --terms "Shakespeare, Dickens, Austen" \
  --match-any \
  --limit 50 \
  --use-mirrors \
  --output ./authors/
```

## Best Practices

1. Always use `--use-db` for better performance and to avoid hitting API limits
2. For large downloads, enable `--use-mirrors` to distribute load and avoid rate limits
3. Use `--skip-existing` to avoid re-downloading books you already have
4. Set a reasonable `--limit` to manage download size
5. Use `--verbose` when troubleshooting issues