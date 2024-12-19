from datetime import datetime
from typing import List, Optional

import pytest

from src.storage.article.interfaces import ArticleSearchIndex, ArticleStorage
from src.storage.article.types import Article, ArticleFilters
from src.storage.base.types import EntityID


class TestArticleStorage(ArticleStorage):
    """Concrete implementation for testing ArticleStorage interface"""

    async def find_by_author(self, author: str) -> List[Article]:
        return []

    async def find_by_source(self, source: str) -> List[Article]:
        return []

    async def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Article]:
        return []

    async def add_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        return True

    async def remove_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        return True

    # Implement required GenericStorage methods
    async def create(self, entity: Article) -> EntityID:
        return EntityID("test_id")

    async def get(self, entity_id: EntityID) -> Optional[Article]:
        return None

    async def update(self, entity_id: EntityID, entity: Article) -> bool:
        return True

    async def delete(self, entity_id: EntityID) -> bool:
        return True

    async def list(self) -> List[Article]:
        return []

    async def read(self, entity_id: EntityID) -> Optional[Article]:
        return None


class TestArticleSearchIndex(ArticleSearchIndex):
    """Concrete implementation for testing ArticleSearchIndex interface"""

    async def search_by_content(
        self, query: str, filters: Optional[ArticleFilters] = None, limit: int = 10
    ) -> List[EntityID]:
        return []

    async def search_by_title(
        self, query: str, filters: Optional[ArticleFilters] = None, limit: int = 10
    ) -> List[EntityID]:
        return []

    async def search_by_tags(
        self, tags: List[str], match_all: bool = False, limit: int = 10
    ) -> List[EntityID]:
        return []

    async def index(self, entity_id: EntityID, entity: Article) -> bool:
        return True

    async def search(self, query: str, limit: int = 10) -> List[EntityID]:
        return []

    async def delete_from_index(self, entity_id: EntityID) -> bool:
        return True

    async def find_similar(
        self, entity_id: EntityID, limit: int = 10
    ) -> List[EntityID]:
        return []


@pytest.mark.asyncio
async def test_article_storage_interface():
    """Test ArticleStorage interface methods"""
    storage = TestArticleStorage()

    # Test find_by_author
    authors = await storage.find_by_author("Test Author")
    assert isinstance(authors, list)

    # Test find_by_source
    sources = await storage.find_by_source("Test Source")
    assert isinstance(sources, list)

    # Test find_by_date_range
    now = datetime.now()
    date_range = await storage.find_by_date_range(now, now)
    assert isinstance(date_range, list)

    # Test add_tags
    success = await storage.add_tags(EntityID("test"), ["tag1", "tag2"])
    assert isinstance(success, bool)

    # Test remove_tags
    success = await storage.remove_tags(EntityID("test"), ["tag1"])
    assert isinstance(success, bool)


@pytest.mark.asyncio
async def test_article_search_index_interface():
    """Test ArticleSearchIndex interface methods"""
    search_index = TestArticleSearchIndex()

    # Test search_by_content
    content_results = await search_index.search_by_content("test query")
    assert isinstance(content_results, list)

    # Test search_by_title
    title_results = await search_index.search_by_title("test title")
    assert isinstance(title_results, list)

    # Test search_by_tags
    tag_results = await search_index.search_by_tags(["tag1", "tag2"])
    assert isinstance(tag_results, list)

    # Test with filters - using correct field names from ArticleFilters
    filters = ArticleFilters(
        author=["author1"],
        source=["source1"],
        published_after=datetime.now(),
        published_before=datetime.now(),
        tags=["tag1"],
    )
    filtered_results = await search_index.search_by_content("test", filters=filters)
    assert isinstance(filtered_results, list)


@pytest.mark.asyncio
async def test_interface_inheritance():
    """Test that interfaces properly inherit from generic interfaces"""
    storage = TestArticleStorage()
    search_index = TestArticleSearchIndex()

    # Test GenericStorage methods
    article = Article(
        title="Test",
        content="Test content",
        author="Test Author",
        source="Test Source",
        published_at=datetime.now(),
        tags=["test"],
    )

    entity_id = await storage.create(article)
    assert isinstance(entity_id, str)

    # Test GenericSearchIndex methods
    success = await search_index.index(entity_id, article)
    assert isinstance(success, bool)
