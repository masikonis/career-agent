import os
import shutil

import pytest

from src.cache import CacheManager


@pytest.fixture
def cache_manager():
    """Fixture to create a CacheManager instance for testing."""
    cache_directory = "test_cache_directory"
    cache = CacheManager(cache_directory=cache_directory)
    yield cache
    # Cleanup after tests
    cache.clear()
    shutil.rmtree(cache_directory)  # Remove the directory and its contents


def test_set_and_get(cache_manager):
    """Test setting and getting a value in the cache."""
    cache_manager.set("key1", "value1")
    assert cache_manager.get("key1") == "value1"


def test_get_non_existent_key(cache_manager):
    """Test getting a value for a non-existent key."""
    assert cache_manager.get("non_existent_key") is None


def test_clear(cache_manager):
    """Test clearing the cache."""
    cache_manager.set("key1", "value1")
    cache_manager.clear()
    assert cache_manager.get("key1") is None
