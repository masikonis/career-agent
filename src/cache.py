from diskcache import Cache


class CacheManager:
    def __init__(self, cache_directory: str = "cache_directory"):
        self.cache = Cache(cache_directory)

    def set(self, key: str, value: any) -> None:
        """Store a value in the cache with the given key."""
        self.cache.set(key, value)

    def get(self, key: str) -> any:
        """Retrieve a value from the cache by key. Returns None if not found."""
        return self.cache.get(key)

    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
