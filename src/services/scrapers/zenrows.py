from typing import Dict, Any
from src.config.settings import config
from zenrows import ZenRowsClient

class ZenrowsScraper:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config['ZENROWS_API_KEY']
        if not self.api_key:
            raise ValueError("ZenRows API key not found")
        self.client = ZenRowsClient(self.api_key)

    async def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape data from given URL using ZenRows"""
        try:
            response = self.client.get(url)
            return {"html": response.text, "status": response.status_code}
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            raise
