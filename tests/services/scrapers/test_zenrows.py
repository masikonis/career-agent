import pytest

from src.services.scrapers.zenrows import ScraperResponse, ZenrowsScraper


@pytest.fixture
def scraper():
    """Fixture to create a scraper instance"""
    return ZenrowsScraper()

@pytest.mark.asyncio
async def test_successful_scrape(scraper):
    """Test successful scraping of a valid URL"""
    url = "https://www.startengine.com/explore"
    response = await scraper.scrape(url)
    
    assert isinstance(response, ScraperResponse)
    assert response.status == 200
    assert len(response.html) > 0
    assert response.url == url
    assert response.error is None
    assert response.metadata is not None
    assert 'headers' in response.metadata
    assert 'params_used' in response.metadata

@pytest.mark.asyncio
async def test_invalid_url(scraper):
    """Test handling of invalid URLs"""
    with pytest.raises(ValueError, match="Invalid URL"):
        await scraper.scrape("not-a-valid-url")

@pytest.mark.asyncio
async def test_scrape_multiple(scraper):
    """Test batch scraping functionality"""
    urls = [
        "https://www.startengine.com/explore",
        "https://www.startengine.com/raises"
    ]
    
    responses = await scraper.scrape_multiple(urls)
    
    assert len(responses) == len(urls)
    for response in responses:
        assert isinstance(response, ScraperResponse)
        assert response.status == 200
        assert len(response.html) > 0

@pytest.mark.asyncio
async def test_custom_options(scraper):
    """Test scraping with custom options"""
    url = "https://www.startengine.com/explore"
    response = await scraper.scrape(
        url,
        js_render=True,
        wait=10,
        retries=2
    )
    
    assert isinstance(response, ScraperResponse)
    assert response.status == 200
    assert response.metadata['params_used']['js_render'] is True
    assert response.metadata['params_used']['wait'] == 10

@pytest.mark.asyncio
async def test_error_handling(scraper):
    """Test error handling with invalid domain"""
    url = "https://non-existent-domain-12345.com"
    response = await scraper.scrape(url)
    
    assert isinstance(response, ScraperResponse)
    assert response.status == 404
    assert response.error is None
    assert "Site not found" in response.html
    assert response.metadata is not None
    assert 'headers' in response.metadata
    assert 'Content-Type' in response.metadata['headers']
    assert response.metadata['headers']['Content-Type'] == 'application/problem+json'
