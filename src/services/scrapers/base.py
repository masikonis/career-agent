from abc import ABC, abstractmethod
from typing import Dict, Any

class WebScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape data from given URL"""
        pass