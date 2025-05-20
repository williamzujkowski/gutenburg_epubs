"""Configuration constants for Gutenberg Downloader."""

from pathlib import Path

# Project Gutenberg base URL
BASE_URL = "https://www.gutenberg.org"

# User agent string - IMPORTANT: Update with your project URL
DEFAULT_USER_AGENT = (
    "GutenbergEPUBCrawler/0.1.0 (+william.zujkowski@gmail.com)"
)

# Rate limiting
DEFAULT_DELAY_SECONDS = 1.0  # Delay between requests in seconds
MIN_DELAY_SECONDS = 0.5  # Minimum allowed delay

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5.0
RETRY_BACKOFF_FACTOR = 2.0

# Download configuration
DEFAULT_DOWNLOAD_DIR = Path("downloads")
CHUNK_SIZE = 8192  # Bytes to read at a time when downloading
MAX_DOWNLOAD_RETRIES = 3  # Maximum retry attempts for downloads
MIN_DELAY_BETWEEN_REQUESTS = 1.0  # Minimum delay between requests

# File formats
EPUB_MIME_TYPE = "application/epub+zip"
EPUB_EXTENSION = ".epub"

# Timeout configuration
DEFAULT_TIMEOUT_SECONDS = 30.0
ROBOTS_TXT_TIMEOUT_SECONDS = 10.0
REQUEST_TIMEOUT = 30.0  # General request timeout

# Async configuration
DEFAULT_CONCURRENT_DOWNLOADS = 5
MAX_CONCURRENT_DOWNLOADS = 15

# Project Gutenberg specific paths
ROBOTS_TXT_PATH = "/robots.txt"
EPUB_PATH_PATTERN = "/ebooks/{book_id}.epub"
BOOK_PATH_PATTERN = "/ebooks/{book_id}"

# Language codes
ENGLISH_LANGUAGE_CODE = "en"

# Project Gutenberg catalog
# Update if needed
DEFAULT_CATALOG_URL = "https://www.gutenberg.org/dirs/GUTINDEX.ALL"

# Mirror site configuration
DEFAULT_MIRRORS_CONFIG_URL = "https://www.gutenberg.org/dirs/MIRRORS.ALL"
DEFAULT_MIRROR_HEALTH_CHECK_TIMEOUT = 10.0
MIRROR_ROTATION_ENABLED = True  # Enable mirror rotation by default
DEFAULT_MIRROR_RETRY_COUNT = 3  # Number of different mirrors to try before failing
DEFAULT_MIRROR_FAILURE_THRESHOLD = 3  # Number of failures before deactivating a mirror
DEFAULT_MIRROR_HEALTH_MIN = 0.1  # Minimum health score for a mirror
DEFAULT_MIRROR_HEALTH_MAX = 1.0  # Maximum health score for a mirror
DEFAULT_MIRROR_HEALTH_RECOVERY_RATE = 0.1  # How quickly a mirror recovers health
DEFAULT_MIRROR_HEALTH_DECAY_RATE = 0.2  # How quickly a mirror loses health