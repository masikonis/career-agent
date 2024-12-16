import pytest
from src.services.scrapers.zenrows import ZenrowsScraper

@pytest.mark.asyncio
async def test_zenrows_scraper():
    # Initialize scraper
    scraper = ZenrowsScraper()
    
    # Test URL (StartEngine's public page)
    url = "https://www.startengine.com/explore"
    
    # Attempt scrape
    result = await scraper.scrape(url)
    
    # Verify response structure
    assert "html" in result
    assert "status" in result
    assert result["status"] == 200
    assert len(result["html"]) > 0
