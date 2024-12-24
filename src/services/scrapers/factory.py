# src/services/scrapers/factory.py
from src.config import config
from src.services.scrapers.base import BaseScraper
from src.services.scrapers.zenrows import ZenrowsScraper


def get_scraper() -> BaseScraper:
    """Factory function to get the appropriate scraper based on configuration."""
    if config["SCRAPER_PROVIDER"] == "zenrows":
        return ZenrowsScraper(api_key=config["ZENROWS_API_KEY"])
    raise ValueError("No valid scraper provider found")
