import asyncio
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from zenrows import ZenRowsClient

from src.cache import CacheManager
from src.config import config
from src.services.scrapers.base import BaseScraper, ScraperResponse
from src.utils.logger import get_logger


class ZenrowsScraper(BaseScraper):
    def __init__(self, api_key: str = None, options: Dict[str, Any] = None):
        """Initialize ZenRows scraper with API key and options"""
        self.api_key = api_key or config["ZENROWS_API_KEY"]
        if not self.api_key:
            raise ValueError("ZenRows API key not found")

        self.options = options or {}
        self.client = ZenRowsClient(self.api_key)
        self.logger = get_logger(__name__)
        self.cache = CacheManager()

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
            "js_render": True,
            "wait": kwargs.get("wait", 5),
            **self.options,
            **kwargs,
        }
        return params

    def _generate_cache_key(self, url: str, params: Dict[str, Any]) -> str:
        """Generate a unique cache key based on URL and parameters"""
        # Serialize the parameters to ensure consistent ordering
        params_str = json.dumps(params, sort_keys=True)
        return f"{url}:{params_str}"

    async def scrape(self, url: str, retries: int = 3, **kwargs) -> ScraperResponse:
        """Scrape data from given URL using ZenRows"""
        if not self._validate_url(url):
            raise ValueError(f"Invalid URL: {url}")

        params = self._prepare_request_params(**kwargs)
        cache_key = self._generate_cache_key(url, params)

        # Check cache first
        cached_response = self.cache.get(cache_key)
        if cached_response:
            self.logger.info(
                f"Returning cached response for {url} with params {params}"
            )
            return cached_response

        last_error = None

        for attempt in range(retries):
            try:
                self.logger.info(
                    f"Scraping {url} (attempt {attempt + 1}/{retries}) with params {params}"
                )
                response = self.client.get(url, params=params)

                # Create ScraperResponse object
                scraper_response = ScraperResponse(
                    html=response.text,
                    status=response.status_code,
                    url=url,
                    metadata={
                        "headers": dict(response.headers),
                        "params_used": params,
                        "attempt": attempt + 1,
                    },
                )

                # Cache the response
                self.cache.set(cache_key, scraper_response)
                return scraper_response

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
                        metadata={"attempts": attempt + 1},
                    )

    async def scrape_multiple(self, urls: List[str], **kwargs) -> List[ScraperResponse]:
        """Scrape multiple URLs"""
        tasks = [self.scrape(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks)
        return results
