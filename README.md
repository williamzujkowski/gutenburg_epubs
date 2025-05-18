# Gutenberg EPUB Downloader

A Python tool for discovering and downloading EPUB books from Project Gutenberg, with both synchronous and asynchronous capabilities.

## Features

- =Ú Discover popular English books with EPUB files
- = Search for books by title or author
-  Download individual or multiple EPUB files
- ¡ Asynchronous concurrent downloads for improved performance
- =Ê Catalog statistics and insights
- > Rate limiting and robots.txt compliance
- =È Progress bars for download tracking
- =á Comprehensive error handling and retry logic

## Installation

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

## Usage

### Discover Popular Books

List popular English books with EPUB files:

```bash
# Show top 10 books (simple format)
gutenberg-downloader discover

# Show top 20 books with detailed information
gutenberg-downloader discover --limit 20 --format detailed

# Use async mode for faster discovery
gutenberg-downloader discover --async-mode --limit 50
```

### Download Books

Download a specific book by ID:

```bash
# Download by book ID
gutenberg-downloader download 1342 --output downloads/

# Download with custom filename
gutenberg-downloader download 1342 --output downloads/ --filename "pride_and_prejudice.epub"
```

### Search for Books

Search by title or author:

```bash
# Search by title
gutenberg-downloader search --title "Pride and Prejudice"

# Search by author
gutenberg-downloader search --author "Jane Austen"

# Exact title match
gutenberg-downloader search --title "Pride and Prejudice" --exact
```

### Download Popular Books in Bulk

Download multiple popular books at once:

```bash
# Download top 10 popular books
gutenberg-downloader download-popular --limit 10 --output books/

# Use async mode with high concurrency
gutenberg-downloader download-popular --limit 50 --async-mode --concurrency 10 --output books/

# Skip existing files
gutenberg-downloader download-popular --limit 100 --skip-existing --output books/
```

### View Statistics

Display catalog statistics:

```bash
gutenberg-downloader stats
```

## Performance

The async mode provides significant performance improvements for bulk operations:

| Operation | Sync Mode | Async Mode (concurrency=10) | Speedup |
|-----------|-----------|----------------------------|---------|
| Discover 100 books | ~30s | ~5s | 6x |
| Download 20 books | ~60s | ~10s | 6x |

## API Usage

You can also use the modules programmatically:

```python
from gutenberg_downloader import BookDiscovery, AsyncBookDiscovery

# Synchronous usage
with BookDiscovery() as discovery:
    books = discovery.discover_popular_english_epubs(limit=10)
    for book in books:
        print(f"{book['book_id']}: {book['metadata']['title']}")

# Asynchronous usage
import asyncio

async def main():
    async with AsyncBookDiscovery() as discovery:
        books = await discovery.discover_popular_english_epubs_async(limit=50)
        # Download multiple books concurrently
        results = await discovery.download_multiple_books_async(
            [book['book_id'] for book in books[:10]],
            output_dir="downloads/"
        )

asyncio.run(main())
```

## Configuration

The tool includes several configurable parameters in `constants.py`:

- `DEFAULT_USER_AGENT`: User agent for HTTP requests
- `DEFAULT_DELAY`: Minimum delay between requests (1.0 second)
- `REQUEST_TIMEOUT`: HTTP request timeout (30 seconds)
- `MAX_DOWNLOAD_RETRIES`: Maximum retry attempts (3)

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Type checking
mypy src/

# Linting
ruff check .

# Format code
ruff format .
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- Project Gutenberg for providing free access to thousands of books
- The Python community for excellent libraries used in this project