"""Gutenberg EPUB Downloader - A tool for downloading and managing Project Gutenberg ebooks."""

__version__ = "0.2.0"
__author__ = "William Zujkowski"
__license__ = "MIT"
__email__ = "william.zujkowski@gmail.com"

# Import key components for easier access
from .constants import DEFAULT_USER_AGENT
from .epub_downloader import EpubDownloader
from .async_epub_downloader import AsyncEpubDownloader
from .discovery import BookDiscovery
from .mirror_manager import MirrorManager

# Set up null handler to prevent logging warnings if app doesn't configure logging
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())