"""Web scraper for Project Gutenberg website.

This module provides functionality to scrape Project Gutenberg pages
while respecting robots.txt rules and maintaining polite crawl delays.
"""

import time
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from robotexclusionrulesparser import RobotExclusionRulesParser

from .constants import (
    BASE_URL,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
    ROBOTS_TXT_PATH,
    ROBOTS_TXT_TIMEOUT_SECONDS,
)
from .logger import logger


class GutenbergScraper:
    """Scraper for Project Gutenberg website.

    Handles web scraping tasks while respecting robots.txt rules,
    implementing rate limiting, and providing robust error handling.

    Attributes:
        base_url: The base URL for Project Gutenberg.
        user_agent: User agent string for requests.
        delay: Delay between requests in seconds.
        timeout: Request timeout in seconds.
        last_request_time: Timestamp of the last request.
        robots_parser: Parser for robots.txt rules.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        delay: float = DEFAULT_DELAY_SECONDS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        """Initialize the Gutenberg scraper.

        Args:
            base_url: The base URL for Project Gutenberg.
            user_agent: User agent string for requests.
            delay: Delay between requests in seconds.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url
        self.user_agent = user_agent
        self.delay = delay
        self.timeout = timeout
        self.last_request_time: Optional[float] = None
        self.robots_parser: Optional[RobotExclusionRulesParser] = None

        # Initialize HTTP client with custom headers
        self.client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
        )

        # Load robots.txt rules
        self._load_robots_txt()

        logger.info(
            "Initialized GutenbergScraper",
            extra={
                "base_url": self.base_url,
                "user_agent": self.user_agent,
                "delay": self.delay,
            },
        )

    def __enter__(self) -> "GutenbergScraper":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
        logger.debug("Closed HTTP client")

    def _load_robots_txt(self) -> None:
        """Load and parse robots.txt file."""
        robots_url = urljoin(self.base_url, ROBOTS_TXT_PATH)

        try:
            # Use shorter timeout for robots.txt
            response = self.client.get(robots_url, timeout=ROBOTS_TXT_TIMEOUT_SECONDS)
            response.raise_for_status()

            self.robots_parser = RobotExclusionRulesParser()
            self.robots_parser.parse(response.text)

            logger.info("Successfully loaded robots.txt", extra={"url": robots_url})
        except httpx.HTTPError as e:
            logger.warning(f"Failed to load robots.txt: {e}", extra={"url": robots_url})
            # Initialize empty parser to allow all paths
            self.robots_parser = RobotExclusionRulesParser()

    def _can_fetch_url(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt rules.

        Args:
            url: The URL to check.

        Returns:
            True if the URL can be fetched, False otherwise.
        """
        if not self.robots_parser:
            return True

        return bool(self.robots_parser.is_allowed(self.user_agent, url))

    def _enforce_delay(self) -> None:
        """Enforce crawl delay between requests."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page from Project Gutenberg.

        Args:
            url: The URL to fetch.

        Returns:
            The page content as a string, or None if fetch failed.

        Raises:
            HTTPError: If the request fails.
        """
        # Ensure absolute URL
        if not url.startswith(("http://", "https://")):
            url = urljoin(self.base_url, url)

        # Check robots.txt permission
        if not self._can_fetch_url(url):
            logger.warning("Robots.txt disallows fetching URL", extra={"url": url})
            return None

        # Enforce crawl delay
        self._enforce_delay()

        try:
            logger.debug(f"Fetching URL: {url}")
            response = self.client.get(url)
            response.raise_for_status()

            self.last_request_time = time.time()

            logger.info(
                "Successfully fetched page",
                extra={
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(response.content),
                },
            )

            return response.text

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching page: {e}",
                extra={
                    "url": url,
                    "status_code": e.response.status_code,
                },
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error fetching page: {e}", extra={"url": url})
            raise

    def parse_book_page(self, html_content: str) -> dict[str, Any]:
        """Parse a book page to extract metadata and available formats.

        Args:
            html_content: The HTML content of the book page.

        Returns:
            Dictionary containing book metadata and download links.
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Extract metadata
        metadata = {}

        # Title
        title_element = soup.find("h1", {"itemprop": "name"})
        if title_element:
            metadata["title"] = title_element.get_text(strip=True)

        # Author
        author_element = soup.find("a", {"itemprop": "creator"})
        if author_element:
            metadata["author"] = author_element.get_text(strip=True)

        # Language
        language_element = soup.find("tr", {"property": "dcterms:language"})
        if language_element:
            lang_td = language_element.find("td")
            if lang_td:
                metadata["language"] = lang_td.get_text(strip=True)

        # Download links
        download_links = {}

        # Find all file download links
        file_links = soup.find_all("a", {"type": "application/epub+zip"})
        for link in file_links:
            href = link.get("href")
            if href:
                # Handle relative URLs
                full_url = urljoin(self.base_url, href)
                download_links["epub"] = full_url

        # Also check for links in the files section
        files_section = soup.find("table", {"class": "files"})
        if files_section:
            for row in files_section.find_all("tr"):
                link = row.find("a")
                if link and "epub" in link.get("href", "").lower():
                    href = link.get("href")
                    full_url = urljoin(self.base_url, href)
                    download_links["epub"] = full_url
                    break

        # Extract book ID from meta tag or URL
        book_id = None
        pg_id_meta = soup.find("meta", {"property": "og:url"})
        if pg_id_meta:
            url_content = pg_id_meta.get("content", "")
            # Extract ID from URL like /ebooks/1234
            parts = url_content.rstrip("/").split("/")
            if parts and parts[-1].isdigit():
                book_id = int(parts[-1])

        return {
            "book_id": book_id,
            "metadata": metadata,
            "download_links": download_links,
        }

    def get_popular_books(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get a list of popular books from the browse page.

        Args:
            limit: Maximum number of books to return.

        Returns:
            List of dictionaries containing book information.
        """
        # Start with the popular books page
        browse_url = urljoin(self.base_url, "/browse/scores/top")

        html_content = self.fetch_page(browse_url)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "lxml")
        books = []

        # Find the "Top 100 EBooks yesterday" section
        heading = soup.find("h2", id="books-last1")
        if heading:
            # The ordered list follows the heading
            book_list = heading.find_next_sibling("ol")
            
            if book_list:
                for item in book_list.find_all("li")[:limit]:
                    book_info: dict[str, Any] = {}

                    # Find link to book page
                    link = item.find("a")
                    if link:
                        href = link.get("href")
                        book_info["url"] = urljoin(self.base_url, href)
                        
                        # Extract title and download count from link text
                        text = link.get_text(strip=True)
                        # Text format: "Title by Author (count)"
                        if " by " in text and "(" in text:
                            title_author = text.split("(")[0].strip()
                            download_count = text.split("(")[1].rstrip(")").strip()
                            
                            parts = title_author.split(" by ")
                            book_info["title"] = parts[0].strip()
                            if len(parts) > 1:
                                book_info["author"] = parts[1].strip()
                            
                            try:
                                book_info["download_count"] = int(download_count)
                            except ValueError:
                                pass
                        else:
                            book_info["title"] = text

                        # Extract book ID from URL
                        if "/ebooks/" in href:
                            try:
                                book_id = int(href.split("/ebooks/")[-1].rstrip("/"))
                                book_info["book_id"] = book_id
                            except (ValueError, IndexError):
                                pass

                        if "book_id" in book_info:  # Only add if we found a book ID
                            books.append(book_info)

        # If the first method didn't work, try alternative structure
        if not books:
            # Look for any ordered list on the page
            for ol in soup.find_all("ol"):
                for item in ol.find_all("li")[:limit]:
                    link = item.find("a")
                    if link and "/ebooks/" in link.get("href", ""):
                        book_info = {}
                        href = link.get("href")
                        book_info["url"] = urljoin(self.base_url, href)
                        
                        text = link.get_text(strip=True)
                        book_info["title"] = text.split(" by ")[0].strip() if " by " in text else text
                        
                        # Extract book ID
                        try:
                            book_id = int(href.split("/ebooks/")[-1].rstrip("/"))
                            book_info["book_id"] = book_id
                            books.append(book_info)
                        except (ValueError, IndexError):
                            pass
                
                if books:  # If we found books, stop looking
                    break

        logger.info(f"Found {len(books)} popular books", extra={"limit": limit})
        return books
