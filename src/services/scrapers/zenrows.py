from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from zenrows import ZenRowsClient

from src.config import config
from src.utils.logger import get_logger


@dataclass
class ScraperResponse:
    """Structured response from the scraper"""
    html: str
    status: int
    url: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ZenrowsScraper:
    def __init__(self, api_key: str = None, options: Dict[str, Any] = None):
        """Initialize ZenRows scraper with API key and options
        
        Args:
            api_key: Optional API key (falls back to config)
            options: Optional ZenRows client options (e.g., proxy, js_render, etc.)
        """
        self.api_key = api_key or config['ZENROWS_API_KEY']
        if not self.api_key:
            raise ValueError("ZenRows API key not found")
        
        self.options = options or {}
        self.client = ZenRowsClient(self.api_key)
        self.logger = get_logger(__name__)

    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception as e:
            self.logger.error(f"Invalid URL format: {url}")
            return False

    def _prepare_request_params(self, **kwargs) -> Dict[str, Any]:
        """Prepare request parameters by merging defaults with custom params"""
        params = {
            'js_render': True,  # Enable JavaScript rendering by default
            'wait': 5,         # Wait for page load
            **self.options,    # Apply instance options
            **kwargs          # Apply request-specific options
        }
        return params

    async def scrape(self, 
                     url: str, 
                     retries: int = 3, 
                     **kwargs) -> ScraperResponse:
        """Scrape data from given URL using ZenRows
        
        Args:
            url: Target URL to scrape
            retries: Number of retry attempts
            **kwargs: Additional ZenRows parameters (overwrites defaults)
        
        Returns:
            ScraperResponse object containing results and metadata
        
        Raises:
            ValueError: If URL is invalid
            Exception: For other scraping errors after retries exhausted
        """
        if not self._validate_url(url):
            raise ValueError(f"Invalid URL: {url}")

        params = self._prepare_request_params(**kwargs)
        last_error = None

        for attempt in range(retries):
            try:
                self.logger.info(f"Scraping {url} (attempt {attempt + 1}/{retries})")
                response = self.client.get(url, params=params)
                
                return ScraperResponse(
                    html=response.text,
                    status=response.status_code,
                    url=url,
                    metadata={
                        'headers': dict(response.headers),
                        'params_used': params,
                        'attempt': attempt + 1
                    }
                )

            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}")
                if attempt == retries - 1:
                    self.logger.error(f"All retries failed for {url}")
                    return ScraperResponse(
                        html="",
                        status=500,
                        url=url,
                        error=last_error,
                        metadata={'attempts': attempt + 1}
                    )

    async def scrape_multiple(self, 
                            urls: list[str], 
                            **kwargs) -> list[ScraperResponse]:
        """Scrape multiple URLs
        
        Args:
            urls: List of URLs to scrape
            **kwargs: Parameters passed to scrape method
        
        Returns:
            List of ScraperResponse objects
        """
        results = []
        for url in urls:
            result = await self.scrape(url, **kwargs)
            results.append(result)
        return results
