"""
Base scraper class with common functionality for all data scrapers.
"""
import time
import random
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import ScraperConfig, DEFAULT_SCRAPER

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers.

    Provides common functionality:
    - Rate limiting
    - Retry logic with exponential backoff
    - User agent rotation
    - Session management
    - Error handling
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize the scraper.

        Args:
            config: Scraper configuration (uses defaults if not provided)
        """
        self.config = config or DEFAULT_SCRAPER
        self.session = requests.Session()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._last_request_time: Dict[str, float] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with rotating user agent."""
        return {
            "User-Agent": random.choice(self.config.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _rate_limit(self, domain: str, delay: float) -> None:
        """
        Enforce rate limiting for a specific domain.

        Args:
            domain: Domain identifier for rate limiting
            delay: Minimum seconds between requests
        """
        now = time.time()
        last_request = self._last_request_time.get(domain, 0)
        elapsed = now - last_request

        if elapsed < delay:
            sleep_time = delay - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {domain}")
            time.sleep(sleep_time)

        self._last_request_time[domain] = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _fetch_page(
        self,
        url: str,
        rate_limit_key: str,
        rate_limit_delay: float,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Fetch a page with rate limiting and retry logic.

        Args:
            url: URL to fetch
            rate_limit_key: Domain key for rate limiting
            rate_limit_delay: Delay between requests
            params: Optional query parameters

        Returns:
            Response object

        Raises:
            requests.HTTPError: If request fails after retries
        """
        self._rate_limit(rate_limit_key, rate_limit_delay)

        self.logger.info(f"Fetching: {url}")
        response = self.session.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()

        return response

    def _parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML content into BeautifulSoup object.

        Args:
            html: Raw HTML string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, "lxml")

    def _safe_get_text(
        self,
        element: Optional[Any],
        default: str = "",
        strip: bool = True,
    ) -> str:
        """
        Safely extract text from a BeautifulSoup element.

        Args:
            element: BeautifulSoup element or None
            default: Default value if element is None
            strip: Whether to strip whitespace

        Returns:
            Text content or default
        """
        if element is None:
            return default
        text = element.get_text()
        return text.strip() if strip else text

    def _safe_get_attr(
        self,
        element: Optional[Any],
        attr: str,
        default: str = "",
    ) -> str:
        """
        Safely get an attribute from a BeautifulSoup element.

        Args:
            element: BeautifulSoup element or None
            attr: Attribute name
            default: Default value if element/attr is None

        Returns:
            Attribute value or default
        """
        if element is None:
            return default
        return element.get(attr, default)

    @abstractmethod
    def scrape(self, **kwargs) -> Any:
        """
        Main scraping method to be implemented by subclasses.

        Returns:
            Scraped data in appropriate format
        """
        pass

    @abstractmethod
    def get_data_source_name(self) -> str:
        """Return the name of the data source."""
        pass

    def close(self) -> None:
        """Close the session and clean up resources."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
