from datetime import datetime
from typing import List, Optional

from ..base.types import EntityID
from ..generic.interfaces import GenericSearchIndex, GenericStorage
from .types import Article, ArticleFilters


class ArticleStorage(GenericStorage[Article]):
    """Extended storage interface for article-specific operations"""

    async def find_by_author(self, author: str) -> List[Article]:
        """Find articles by author"""
        pass

    async def find_by_source(self, source: str) -> List[Article]:
        """Find articles by source"""
        pass

    async def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Article]:
        """Find articles within a date range"""
        pass

    async def add_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        """Add tags to an article"""
        pass

    async def remove_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        """Remove tags from an article"""
        pass


class ArticleSearchIndex(GenericSearchIndex[Article]):
    """Extended search interface for article-specific search operations"""

    async def search_by_content(
        self, query: str, filters: Optional[ArticleFilters] = None, limit: int = 10
    ) -> List[EntityID]:
        """Search articles by content with optional filters"""
        pass

    async def search_by_title(
        self, query: str, filters: Optional[ArticleFilters] = None, limit: int = 10
    ) -> List[EntityID]:
        """Search articles by title with optional filters"""
        pass

    async def search_by_tags(
        self, tags: List[str], match_all: bool = False, limit: int = 10
    ) -> List[EntityID]:
        """
        Search articles by tags
        match_all: if True, all tags must match; if False, any tag can match
        """
        pass
