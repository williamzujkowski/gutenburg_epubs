"""Mirror site manager for Project Gutenberg downloads.

This module provides functionality to manage and rotate between different Gutenberg mirror sites
to distribute download requests and avoid rate limiting issues.
"""

import json
import logging
import os
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any
from urllib.parse import urlparse, urljoin

import httpx

from .constants import BASE_URL, REQUEST_TIMEOUT, DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)


@dataclass
class MirrorSite:
    """Represents a Gutenberg mirror site."""
    
    name: str
    base_url: str
    priority: int = 1  # Higher priority mirrors are preferred
    country: Optional[str] = None
    active: bool = True
    health_score: float = 1.0  # 0.0-1.0, higher is better
    last_checked: Optional[float] = None  # Timestamp of last health check
    last_success: Optional[float] = None  # Timestamp of last successful health check


class MirrorManager:
    """Manages selection and rotation of Project Gutenberg mirror sites."""
    
    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = REQUEST_TIMEOUT,
        primary_site: str = BASE_URL,
        config_dir: Optional[str] = None,
    ):
        """Initialize the mirror manager.
        
        Args:
            user_agent: User agent string to use for requests
            timeout: Request timeout in seconds
            primary_site: The primary Gutenberg site URL
            config_dir: Directory to store mirror configuration and health data
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.primary_site = primary_site
        
        # Set up config dir - use user's config directory if not specified
        if config_dir is None:
            home_dir = os.path.expanduser("~")
            self.config_dir = os.path.join(home_dir, ".gutenberg_downloader")
        else:
            self.config_dir = config_dir
            
        # Ensure config dir exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Path to mirrors file
        self.mirrors_file = os.path.join(self.config_dir, "mirrors.json")
        
        # Default mirror sites
        default_mirrors = [
            # Primary official site (default fallback)
            MirrorSite(name="Project Gutenberg Main", base_url=BASE_URL, priority=5, country="US"),
            
            # High priority mirrors
            MirrorSite(name="Project Gutenberg PGLAF", base_url="https://gutenberg.pglaf.org/", priority=4, country="US"),
            MirrorSite(name="Aleph PGLAF", base_url="https://aleph.pglaf.org/", priority=4, country="US"),
            MirrorSite(name="Nabasny", base_url="https://gutenberg.nabasny.com/", priority=3, country="US"),
            
            # Medium priority mirrors
            MirrorSite(name="UK Mirror Service", base_url="http://www.mirrorservice.org/sites/ftp.ibiblio.org/pub/docs/books/gutenberg/", priority=2, country="UK"),
            MirrorSite(name="Xmission", base_url="http://mirrors.xmission.com/gutenberg/", priority=2, country="US"),
            
            # Lower priority mirrors
            MirrorSite(name="University of Minho", base_url="http://eremita.di.uminho.pt/gutenberg/", priority=1, country="PT"),
            MirrorSite(name="University of Waterloo", base_url="http://mirror.csclub.uwaterloo.ca/gutenberg/", priority=1, country="CA"),
        ]
        
        # Try to load mirrors from file, or use defaults
        self.mirrors: List[MirrorSite] = self.load_mirrors() or default_mirrors
        
        # Keep track of recently used mirrors to avoid repeated use
        self.recently_used: List[str] = []
        
        # Track failed requests for each mirror
        self.failure_counts: Dict[str, int] = {mirror.base_url: 0 for mirror in self.mirrors}
        
        # Map of book IDs to mirrors that have them
        self.book_availability: Dict[int, Set[str]] = {}
        
        # Initialize httpclient for health checks
        self.client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
        )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """Close any open resources."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
            
        # Save mirrors when closing
        self.save_mirrors()
        
    def load_mirrors(self) -> Optional[List[MirrorSite]]:
        """Load mirrors from the saved configuration file.
        
        Returns:
            List of MirrorSite objects if successful, None otherwise
        """
        try:
            if not os.path.exists(self.mirrors_file):
                logger.debug(f"Mirrors file not found: {self.mirrors_file}")
                return None
                
            with open(self.mirrors_file, 'r') as f:
                mirrors_data = json.load(f)
                
            mirrors = []
            for mirror_dict in mirrors_data:
                # Convert dict to MirrorSite object
                mirror = MirrorSite(
                    name=mirror_dict["name"],
                    base_url=mirror_dict["base_url"],
                    priority=mirror_dict.get("priority", 1),
                    country=mirror_dict.get("country"),
                    active=mirror_dict.get("active", True),
                    health_score=mirror_dict.get("health_score", 1.0),
                    last_checked=mirror_dict.get("last_checked"),
                    last_success=mirror_dict.get("last_success")
                )
                mirrors.append(mirror)
                
            logger.info(f"Loaded {len(mirrors)} mirrors from {self.mirrors_file}")
            return mirrors
            
        except Exception as e:
            logger.warning(f"Error loading mirrors: {e}")
            return None
            
    def save_mirrors(self) -> bool:
        """Save mirrors to configuration file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert mirrors to serializable dicts
            mirrors_data = []
            for mirror in self.mirrors:
                mirror_dict = {
                    "name": mirror.name,
                    "base_url": mirror.base_url,
                    "priority": mirror.priority,
                    "country": mirror.country,
                    "active": mirror.active,
                    "health_score": mirror.health_score,
                    "last_checked": mirror.last_checked,
                    "last_success": mirror.last_success
                }
                mirrors_data.append(mirror_dict)
                
            with open(self.mirrors_file, 'w') as f:
                json.dump(mirrors_data, f, indent=2)
                
            logger.debug(f"Saved {len(self.mirrors)} mirrors to {self.mirrors_file}")
            return True
            
        except Exception as e:
            logger.warning(f"Error saving mirrors: {e}")
            return False
    
    def _normalize_base_url(self, url: str) -> str:
        """Ensure base URL has a trailing slash and uses HTTPS when possible.
        
        Args:
            url: The URL to normalize
            
        Returns:
            Normalized URL with trailing slash
        """
        # Upgrade HTTP to HTTPS when possible, except for mirrors that don't support HTTPS
        if url.startswith('http://') and not any(domain in url for domain in ['di.uminho.pt', 'csclub.uwaterloo.ca']):
            url = 'https://' + url[7:]
            
        # Ensure URL ends with a slash
        return url.rstrip('/') + '/'
        
    def add_mirror(self, name: str, base_url: str, priority: int = 1, country: Optional[str] = None) -> None:
        """Add a new mirror site to the list.
        
        Args:
            name: Display name of the mirror
            base_url: Base URL of the mirror
            priority: Priority level (higher values are preferred)
            country: Country code of the mirror
        """
        # Normalize the URL
        base_url = self._normalize_base_url(base_url)
            
        # Check if mirror already exists and update it
        for i, mirror in enumerate(self.mirrors):
            if mirror.base_url == base_url:
                self.mirrors[i] = MirrorSite(
                    name=name,
                    base_url=base_url,
                    priority=priority,
                    country=country,
                    active=True,
                    health_score=mirror.health_score
                )
                logger.info(f"Updated mirror: {name} ({base_url})")
                return
                
        # Add new mirror
        self.mirrors.append(
            MirrorSite(
                name=name,
                base_url=base_url,
                priority=priority,
                country=country,
                active=True,
                health_score=1.0
            )
        )
        self.failure_counts[base_url] = 0
        logger.info(f"Added new mirror: {name} ({base_url})")
    
    def remove_mirror(self, base_url: str) -> None:
        """Remove a mirror from the list by URL.
        
        Args:
            base_url: Base URL of the mirror to remove
        """
        for i, mirror in enumerate(self.mirrors):
            if mirror.base_url == base_url:
                self.mirrors.pop(i)
                self.failure_counts.pop(base_url, None)
                if base_url in self.recently_used:
                    self.recently_used.remove(base_url)
                logger.info(f"Removed mirror: {base_url}")
                return
                
        logger.warning(f"Mirror not found for removal: {base_url}")
    
    def get_mirrors(self) -> List[MirrorSite]:
        """Get the list of all mirror sites.
        
        Returns:
            List of MirrorSite objects
        """
        return self.mirrors.copy()
    
    def get_active_mirrors(self) -> List[MirrorSite]:
        """Get only active mirrors.
        
        Returns:
            List of active MirrorSite objects
        """
        return [mirror for mirror in self.mirrors if mirror.active]
    
    def build_book_url(self, book_id: int, mirror_url: str) -> str:
        """Build the URL for a specific book on a specified mirror.
        
        Args:
            book_id: The book ID
            mirror_url: Base URL of the mirror
            
        Returns:
            Complete URL for the book EPUB file
        """
        # Normalize the URL first
        mirror_url = self._normalize_base_url(mirror_url)
        
        # Handle different mirror path structures
        if mirror_url == self._normalize_base_url(BASE_URL) or "gutenberg.org" in mirror_url:
            # Standard Gutenberg URL structure
            return f"{mirror_url.rstrip('/')}/ebooks/{book_id}.epub"
        elif "pglaf.org" in mirror_url:
            # PGLAF structure
            return f"{mirror_url.rstrip('/')}/cache/epub/{book_id}/pg{book_id}.epub"
        elif "nabasny.com" in mirror_url:
            # Nabasny structure
            return f"{mirror_url.rstrip('/')}/{book_id}.epub"
        elif "xmission.com" in mirror_url:
            # xmission structure
            return f"{mirror_url.rstrip('/')}/cache/epub/{book_id}/pg{book_id}.epub"
        else:
            # Generic fallback - most mirrors use this structure
            return f"{mirror_url.rstrip('/')}/cache/epub/{book_id}/pg{book_id}.epub"

    def select_mirror(self, book_id: Optional[int] = None) -> str:
        """Select a mirror site using a weighted algorithm.
        
        Args:
            book_id: Optional book ID to consider availability
            
        Returns:
            Base URL of the selected mirror
        """
        active_mirrors = self.get_active_mirrors()
        
        if not active_mirrors:
            logger.warning("No active mirrors available. Using primary site.")
            return self.primary_site
            
        # If we know which mirrors have this book, prioritize them
        available_mirrors = []
        if book_id and book_id in self.book_availability:
            available_base_urls = {self._normalize_base_url(url) for url in self.book_availability[book_id]}
            available_mirrors = [m for m in active_mirrors if self._normalize_base_url(m.base_url) in available_base_urls]
            
            if available_mirrors:
                active_mirrors = available_mirrors
        
        # Normalize all recently used URLs
        normalized_recently_used = [self._normalize_base_url(url) for url in self.recently_used[-3:]]
        
        # Create pool of candidates based on priority and health
        # Exclude recently used mirrors if possible
        candidates = [
            m for m in active_mirrors 
            if self._normalize_base_url(m.base_url) not in normalized_recently_used or len(active_mirrors) <= 3
        ]
        
        if not candidates:
            # If all mirrors were recently used, use all active mirrors
            candidates = active_mirrors
        
        # Calculate weights based on priority and health score
        weights = [
            (c.priority * c.health_score) / (1 + self.failure_counts[c.base_url] ** 2)
            for c in candidates
        ]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            # Equal probability if all weights are 0
            weights = [1.0 / len(candidates)] * len(candidates)
        
        # Select mirror based on weights
        selected = random.choices(candidates, weights=weights, k=1)[0]
        
        # Track recently used
        self.recently_used.append(selected.base_url)
        if len(self.recently_used) > 10:
            self.recently_used.pop(0)
            
        logger.info(f"Selected mirror: {selected.name} ({selected.base_url})")
        return selected.base_url
    
    def report_failure(self, mirror_url: str) -> None:
        """Report a failure for a specific mirror.
        
        Args:
            mirror_url: Base URL of the mirror that failed
        """
        # Increment failure count
        self.failure_counts[mirror_url] = self.failure_counts.get(mirror_url, 0) + 1
        
        # Update mirror health score
        for i, mirror in enumerate(self.mirrors):
            if mirror.base_url == mirror_url:
                # Decrease health score but not below 0.1
                self.mirrors[i].health_score = max(0.1, mirror.health_score * 0.8)
                
                # If too many failures, mark as inactive temporarily
                from .constants import DEFAULT_MIRROR_FAILURE_THRESHOLD
                if self.failure_counts[mirror_url] > DEFAULT_MIRROR_FAILURE_THRESHOLD:
                    logger.warning(f"Mirror {mirror.name} deactivated due to multiple failures")
                    self.mirrors[i].active = False
                    
                break
                
        logger.info(f"Reported failure for mirror: {mirror_url}")
    
    def report_success(self, mirror_url: str) -> None:
        """Report a successful download from a mirror.
        
        Args:
            mirror_url: Base URL of the mirror that succeeded
        """
        # Reset failure count
        self.failure_counts[mirror_url] = 0
        
        # Update mirror health score
        for i, mirror in enumerate(self.mirrors):
            if mirror.base_url == mirror_url:
                # Increase health score but not above 1.0
                self.mirrors[i].health_score = min(1.0, mirror.health_score * 1.1 + 0.05)
                
                # Ensure mirror is active
                if not mirror.active:
                    logger.info(f"Reactivating mirror: {mirror.name}")
                    self.mirrors[i].active = True
                break
                
        logger.debug(f"Reported success for mirror: {mirror_url}")
    
    def record_book_availability(self, book_id: int, mirror_url: str) -> None:
        """Record that a book is available on a specific mirror.
        
        Args:
            book_id: The book ID
            mirror_url: Base URL of the mirror
        """
        if book_id not in self.book_availability:
            self.book_availability[book_id] = set()
            
        self.book_availability[book_id].add(mirror_url)
    
    async def check_mirror_health_async(self, mirror: MirrorSite) -> bool:
        """Check if a mirror is responsive and update its health score asynchronously.
        
        Args:
            mirror: The MirrorSite to check
            
        Returns:
            True if the mirror is healthy, False otherwise
        """
        test_url = mirror.base_url
        current_time = time.time()
        mirror.last_checked = current_time
        
        try:
            # Use the imported httpx module, not a local import
            async with httpx.AsyncClient(
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.head(test_url)
                
                if response.status_code < 400:
                    # Success - increase health score
                    from .constants import DEFAULT_MIRROR_HEALTH_MAX, DEFAULT_MIRROR_HEALTH_RECOVERY_RATE
                    mirror.health_score = min(DEFAULT_MIRROR_HEALTH_MAX, 
                                             mirror.health_score + DEFAULT_MIRROR_HEALTH_RECOVERY_RATE)
                    self.failure_counts[mirror.base_url] = 0
                    mirror.active = True
                    mirror.last_success = current_time
                    return True
                else:
                    # Decrease health on HTTP error
                    from .constants import DEFAULT_MIRROR_HEALTH_MIN, DEFAULT_MIRROR_FAILURE_THRESHOLD, DEFAULT_MIRROR_HEALTH_DECAY_RATE
                    mirror.health_score = max(DEFAULT_MIRROR_HEALTH_MIN, 
                                             mirror.health_score - DEFAULT_MIRROR_HEALTH_DECAY_RATE)
                    self.failure_counts[mirror.base_url] = self.failure_counts.get(mirror.base_url, 0) + 1
                    
                    if self.failure_counts[mirror.base_url] > DEFAULT_MIRROR_FAILURE_THRESHOLD:
                        mirror.active = False
                        
                    return False
                    
        except Exception as e:
            logger.warning(f"Error checking mirror health for {mirror.name}: {e}")
            from .constants import DEFAULT_MIRROR_HEALTH_MIN, DEFAULT_MIRROR_FAILURE_THRESHOLD
            # More severe penalty for connection failures
            mirror.health_score = max(DEFAULT_MIRROR_HEALTH_MIN, mirror.health_score - 0.3)
            self.failure_counts[mirror.base_url] = self.failure_counts.get(mirror.base_url, 0) + 1
            
            if self.failure_counts[mirror.base_url] > DEFAULT_MIRROR_FAILURE_THRESHOLD:
                mirror.active = False
                
            return False
    
    def check_mirror_health(self, mirror: MirrorSite) -> bool:
        """Check if a mirror is responsive and update its health score synchronously.
        
        Args:
            mirror: The MirrorSite to check
            
        Returns:
            True if the mirror is healthy, False otherwise
        """
        test_url = mirror.base_url
        current_time = time.time()
        mirror.last_checked = current_time
        
        try:
            response = self.client.head(test_url, follow_redirects=True)
            
            if response.status_code < 400:
                # Success - increase health score
                from .constants import DEFAULT_MIRROR_HEALTH_MAX, DEFAULT_MIRROR_HEALTH_RECOVERY_RATE
                mirror.health_score = min(DEFAULT_MIRROR_HEALTH_MAX, 
                                         mirror.health_score + DEFAULT_MIRROR_HEALTH_RECOVERY_RATE)
                self.failure_counts[mirror.base_url] = 0
                mirror.active = True
                mirror.last_success = current_time
                
                # Save mirrors data after successful checks
                if random.random() < 0.1:  # Randomly save ~10% of the time to avoid excessive writes
                    self.save_mirrors()
                    
                return True
            else:
                # Decrease health on HTTP error
                from .constants import DEFAULT_MIRROR_HEALTH_MIN, DEFAULT_MIRROR_FAILURE_THRESHOLD, DEFAULT_MIRROR_HEALTH_DECAY_RATE
                mirror.health_score = max(DEFAULT_MIRROR_HEALTH_MIN, 
                                         mirror.health_score - DEFAULT_MIRROR_HEALTH_DECAY_RATE)
                self.failure_counts[mirror.base_url] = self.failure_counts.get(mirror.base_url, 0) + 1
                
                if self.failure_counts[mirror.base_url] > DEFAULT_MIRROR_FAILURE_THRESHOLD:
                    mirror.active = False
                    
                return False
                
        except Exception as e:
            logger.warning(f"Error checking mirror health for {mirror.name}: {e}")
            from .constants import DEFAULT_MIRROR_HEALTH_MIN, DEFAULT_MIRROR_FAILURE_THRESHOLD
            # More severe penalty for connection failures
            mirror.health_score = max(DEFAULT_MIRROR_HEALTH_MIN, mirror.health_score - 0.3)
            self.failure_counts[mirror.base_url] = self.failure_counts.get(mirror.base_url, 0) + 1
            
            if self.failure_counts[mirror.base_url] > DEFAULT_MIRROR_FAILURE_THRESHOLD:
                mirror.active = False
                
            return False
    
    async def check_all_mirrors_async(self) -> Dict[str, bool]:
        """Check health of all configured mirrors asynchronously.
        
        Returns:
            Dictionary mapping mirror URLs to health status
        """
        results = {}
        import asyncio
        
        # Create tasks for checking all mirrors concurrently
        tasks = [self.check_mirror_health_async(mirror) for mirror in self.mirrors]
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, mirror in enumerate(self.mirrors):
            result = health_results[i]
            if isinstance(result, Exception):
                logger.error(f"Error checking mirror {mirror.name}: {result}")
                results[mirror.base_url] = False
            else:
                results[mirror.base_url] = result
            
        return results
    
    def check_all_mirrors(self) -> Dict[str, bool]:
        """Check health of all configured mirrors synchronously.
        
        Returns:
            Dictionary mapping mirror URLs to health status
        """
        results = {}
        
        for mirror in self.mirrors:
            healthy = self.check_mirror_health(mirror)
            results[mirror.base_url] = healthy
            
        return results
    
    def get_book_url(self, book_id: int) -> str:
        """Get the URL for a book from an optimal mirror.
        
        Args:
            book_id: The book ID
            
        Returns:
            Complete URL for the book EPUB file
        """
        mirror_url = self.select_mirror(book_id)
        return self.build_book_url(book_id, mirror_url)