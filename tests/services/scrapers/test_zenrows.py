from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.scrapers.zenrows import ScraperResponse, ZenrowsScraper


@pytest.fixture
def mock_zenrows_client(mocker):
    """Fixture to mock ZenRowsClient."""
    mock_client = MagicMock()
    mock_client.get = MagicMock()
    mocker.patch(
        "src.services.scrapers.zenrows.ZenRowsClient", return_value=mock_client
    )
    return mock_client


@pytest.fixture
def mock_cache_manager(mocker):
    """Fixture to mock CacheManager."""
    mock_cache = MagicMock()
    mock_cache.get = MagicMock(return_value=None)
    mock_cache.set = MagicMock()
    mocker.patch("src.services.scrapers.zenrows.CacheManager", return_value=mock_cache)
    return mock_cache


@pytest.fixture
def mock_logger(mocker):
    """Fixture to mock the logger."""
    mock_log = MagicMock()
    mocker.patch("src.services.scrapers.zenrows.get_logger", return_value=mock_log)
    return mock_log


@pytest.fixture
def scraper(mock_zenrows_client, mock_cache_manager, mock_logger):
    """Fixture to create a scraper instance with mocked dependencies."""
    return ZenrowsScraper()


@pytest.mark.asyncio
async def test_successful_scrape(scraper, mock_zenrows_client, mock_cache_manager):
    """Test successful scraping of a valid URL."""
    url = "https://www.startengine.com/explore"
    mock_response = MagicMock()
    mock_response.text = "<html>Content</html>"
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_zenrows_client.get.return_value = mock_response

    response = await scraper.scrape(url)

    # Assertions
    assert isinstance(response, ScraperResponse)
    assert response.status == 200
    assert response.html == "<html>Content</html>"
    assert response.url == url
    assert response.error is None
    assert response.metadata is not None
    assert response.metadata["headers"] == {"Content-Type": "text/html"}
    assert response.metadata["params_used"]["js_render"] is True
    assert response.metadata["params_used"]["wait"] == 5  # Default wait
    assert mock_cache_manager.get.called
    assert mock_cache_manager.set.called


@pytest.mark.asyncio
async def test_invalid_url(scraper):
    """Test handling of invalid URLs."""
    invalid_url = "not-a-valid-url"
    with pytest.raises(ValueError, match="Invalid URL"):
        await scraper.scrape(invalid_url)


@pytest.mark.asyncio
async def test_scrape_multiple(scraper, mock_zenrows_client, mock_cache_manager):
    """Test batch scraping functionality."""
    urls = ["https://www.startengine.com/explore", "https://www.startengine.com/raises"]

    # Mock responses for each URL
    mock_response1 = MagicMock()
    mock_response1.text = "<html>Explore Content</html>"
    mock_response1.status_code = 200
    mock_response1.headers = {"Content-Type": "text/html"}

    mock_response2 = MagicMock()
    mock_response2.text = "<html>Raises Content</html>"
    mock_response2.status_code = 200
    mock_response2.headers = {"Content-Type": "text/html"}

    # Configure the mock to return different responses based on input URL
    def get_side_effect(url, params):
        if url == urls[0]:
            return mock_response1
        elif url == urls[1]:
            return mock_response2
        else:
            raise ValueError("Unknown URL")

    mock_zenrows_client.get.side_effect = get_side_effect

    responses = await scraper.scrape_multiple(urls)

    # Assertions
    assert len(responses) == 2
    assert responses[0].html == "<html>Explore Content</html>"
    assert responses[0].status == 200
    assert responses[0].url == urls[0]
    assert responses[0].error is None

    assert responses[1].html == "<html>Raises Content</html>"
    assert responses[1].status == 200
    assert responses[1].url == urls[1]
    assert responses[1].error is None

    # Ensure cache was checked and set for each URL
    assert mock_cache_manager.get.call_count == 2
    assert mock_cache_manager.set.call_count == 2


@pytest.mark.asyncio
async def test_custom_options(scraper, mock_zenrows_client, mock_cache_manager):
    """Test scraping with custom options."""
    url = "https://www.startengine.com/explore"
    custom_options = {"js_render": True, "wait": 10, "retries": 2}

    mock_response = MagicMock()
    mock_response.text = "<html>Custom Content</html>"
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_zenrows_client.get.return_value = mock_response

    response = await scraper.scrape(url, **custom_options)

    # Assertions
    assert isinstance(response, ScraperResponse)
    assert response.status == 200
    assert response.html == "<html>Custom Content</html>"
    assert response.url == url
    assert response.error is None
    assert response.metadata is not None
    assert response.metadata["params_used"]["js_render"] is True
    assert response.metadata["params_used"]["wait"] == 10
    assert response.metadata["attempt"] == 1  # First attempt

    # Ensure cache was checked and set with custom parameters
    expected_params = {"js_render": True, "wait": 10, "retries": 2}
    mock_cache_manager.get.assert_called_once()
    mock_cache_manager.set.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling(
    scraper, mock_zenrows_client, mock_cache_manager, mock_logger
):
    """Test error handling with invalid domain."""
    url = "https://non-existent-domain-12345.com"

    # Configure the mock to raise an exception
    mock_zenrows_client.get.side_effect = Exception("Site not found")

    response = await scraper.scrape(url, retries=2)

    # Assertions
    assert isinstance(response, ScraperResponse)
    assert response.status == 500
    assert response.html == ""
    assert response.url == url
    assert response.error == "Site not found"
    assert response.metadata is not None
    assert response.metadata["attempts"] == 2

    # Ensure cache was not set due to failure
    mock_cache_manager.get.assert_called_once()
    mock_cache_manager.set.assert_not_called()

    # Check that error was logged
    assert mock_logger.warning.call_count == 2
    assert mock_logger.error.called


@pytest.mark.asyncio
async def test_cache_hit(scraper, mock_zenrows_client, mock_cache_manager):
    """Test that cached responses are returned without making a new request."""
    url = "https://www.startengine.com/explore"

    # Prepare a cached response
    cached_response = ScraperResponse(
        html="<html>Cached Content</html>",
        status=200,
        url=url,
        metadata={
            "headers": {"Content-Type": "text/html"},
            "params_used": {"js_render": True, "wait": 5},
            "attempt": 1,
        },
    )
    mock_cache_manager.get.return_value = cached_response

    response = await scraper.scrape(url)

    # Assertions
    assert response == cached_response

    # Ensure that the client was not called since response was cached
    mock_zenrows_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_cache_separate_keys(scraper, mock_zenrows_client, mock_cache_manager):
    """Test that different parameters generate separate cache keys."""
    url = "https://www.startengine.com/explore"

    # First scrape with default parameters
    mock_response1 = MagicMock()
    mock_response1.text = "<html>Default Content</html>"
    mock_response1.status_code = 200
    mock_response1.headers = {"Content-Type": "text/html"}
    mock_zenrows_client.get.return_value = mock_response1

    response1 = await scraper.scrape(url)

    # Second scrape with custom wait parameter
    mock_response2 = MagicMock()
    mock_response2.text = "<html>Custom Wait Content</html>"
    mock_response2.status_code = 200
    mock_response2.headers = {"Content-Type": "text/html"}
    mock_zenrows_client.get.return_value = mock_response2

    response2 = await scraper.scrape(url, wait=10)

    # Assertions
    assert response1.html == "<html>Default Content</html>"
    assert response2.html == "<html>Custom Wait Content</html>"

    # Ensure that cache was checked twice with different keys
    assert mock_cache_manager.get.call_count == 2
    assert mock_cache_manager.set.call_count == 2

    # Ensure that the client was called twice since cache keys are different
    assert mock_zenrows_client.get.call_count == 2
