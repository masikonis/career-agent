from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ScraperResponse:
    """Structured response from the scraper"""

    html: str
    status: int
    url: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WebScraper(ABC):
    """Base class for web scrapers"""

    @abstractmethod
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        pass

    @abstractmethod
    def _prepare_request_params(self, **kwargs) -> Dict[str, Any]:
        """Prepare request parameters"""
        pass

    @abstractmethod
    async def scrape(self, url: str, retries: int = 3, **kwargs) -> ScraperResponse:
        """Scrape data from given URL

        Args:
            url: Target URL to scrape
            retries: Number of retry attempts
            **kwargs: Additional scraper-specific parameters

        Returns:
            ScraperResponse object containing results and metadata

        Raises:
            ValueError: If URL is invalid
            Exception: For other scraping errors after retries exhausted
        """
        pass

    @abstractmethod
    async def scrape_multiple(self, urls: List[str], **kwargs) -> List[ScraperResponse]:
        """Scrape multiple URLs

        Args:
            urls: List of URLs to scrape
            **kwargs: Parameters passed to scrape method

        Returns:
            List of ScraperResponse objects
        """
        pass
