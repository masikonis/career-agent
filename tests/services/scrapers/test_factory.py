from unittest.mock import patch

import pytest

from src.config import config
from src.services.scrapers.factory import get_scraper
from src.services.scrapers.zenrows import ZenrowsScraper


# Mock the configuration for testing
@pytest.fixture(autouse=True)
def mock_config():
    with patch.dict(
        config, {"SCRAPER_PROVIDER": "zenrows", "ZENROWS_API_KEY": "test_api_key"}
    ):
        yield


def test_get_scraper_returns_zenrows():
    """Test that the factory returns an instance of ZenrowsScraper."""
    scraper = get_scraper()
    assert isinstance(scraper, ZenrowsScraper), "Expected ZenrowsScraper instance"


def test_get_scraper_invalid_provider():
    """Test that the factory raises ValueError for an invalid provider."""
    with patch.dict(config, {"SCRAPER_PROVIDER": "invalid_provider"}):
        with pytest.raises(ValueError, match="No valid scraper provider found"):
            get_scraper()
