from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

from ..base.exceptions import EntityNotFoundError, StorageError
from ..base.types import EntityID
from ..generic.manager import EntityStorageManager
from .interfaces import ArticleSearchIndex, ArticleStorage
from .types import Article, ArticleFilters

logger = get_logger(__name__)


class ArticleManager(EntityStorageManager[Article]):
    """Manager for article storage and search operations"""

    def __init__(
        self,
        storage: ArticleStorage,
        search_index: ArticleSearchIndex,
    ):
        super().__init__(storage, search_index, "article")
        # Type-specific references
        self.article_storage = storage
        self.article_search = search_index

    async def create_article(
        self,
        title: str,
        content: str,
        author: str,
        source: str,
        published_at: datetime,
        tags: Optional[List[str]] = None,
        url: Optional[str] = None,
    ) -> EntityID:
        """Create a new article with all necessary fields"""
        try:
            article = Article(
                title=title,
                content=content,
                author=author,
                source=source,
                published_at=published_at,
                tags=tags or [],
                url=url,
            )

            # Validate article
            if not article.validate():
                raise StorageError("Invalid article data")

            # Create article using base class method
            return await self.create(article)

        except Exception as e:
            logger.error(f"Failed to create article: {str(e)}")
            raise StorageError(f"Failed to create article: {str(e)}")

    async def update_article(
        self,
        article_id: EntityID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        author: Optional[str] = None,
        source: Optional[str] = None,
        published_at: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        url: Optional[str] = None,
    ) -> bool:
        """Update an existing article with optional fields"""
        try:
            # Get existing article
            article = await self.get(article_id)
            if not article:
                raise EntityNotFoundError("article", article_id)

            # Update fields if provided
            if title is not None:
                article.title = title
            if content is not None:
                article.content = content
            if author is not None:
                article.author = author
            if source is not None:
                article.source = source
            if published_at is not None:
                article.published_at = published_at
            if tags is not None:
                article.tags = tags
            if url is not None:
                article.url = url

            # Update timestamp
            article.updated_at = datetime.now()

            # Validate updated article
            if not article.validate():
                raise StorageError("Invalid article data after update")

            # Update using base class method
            return await self.update(article_id, article)

        except Exception as e:
            logger.error(f"Failed to update article {article_id}: {str(e)}")
            raise StorageError(f"Failed to update article: {str(e)}")

    async def add_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        """Add tags to an article"""
        try:
            article = await self.get(article_id)
            if not article:
                raise EntityNotFoundError("article", article_id)

            # Add new tags without duplicates
            current_tags = set(article.tags)
            current_tags.update(tags)
            article.tags = list(current_tags)

            # Update article
            return await self.update(article_id, article)

        except Exception as e:
            logger.error(f"Failed to add tags to article {article_id}: {str(e)}")
            raise StorageError(f"Failed to add tags: {str(e)}")

    async def remove_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        """Remove tags from an article"""
        try:
            article = await self.get(article_id)
            if not article:
                raise EntityNotFoundError("article", article_id)

            # Remove specified tags
            article.tags = [tag for tag in article.tags if tag not in tags]

            # Update article
            return await self.update(article_id, article)

        except Exception as e:
            logger.error(f"Failed to remove tags from article {article_id}: {str(e)}")
            raise StorageError(f"Failed to remove tags: {str(e)}")

    async def search_by_filters(
        self, query: str, filters: Optional[ArticleFilters] = None, limit: int = 10
    ) -> List[Article]:
        """Search articles with optional filters"""
        try:
            # Convert filters to search index format
            filter_dict = filters.to_dict() if filters else {}

            # Search using base class method
            article_ids = await self.search(query, filter_dict, limit)

            # Fetch full articles
            articles = []
            for article_id in article_ids:
                article = await self.get(article_id)
                if article:
                    articles.append(article)

            return articles

        except Exception as e:
            logger.error(f"Failed to search articles with filters: {str(e)}")
            raise StorageError(f"Failed to search articles: {str(e)}")

    async def find_similar_articles(
        self, article_id: EntityID, limit: int = 10
    ) -> List[Article]:
        """Find articles similar to the given article"""
        try:
            # Get similar article IDs
            similar_ids = await self.find_similar(article_id, limit)

            # Fetch full articles
            similar_articles = []
            for similar_id in similar_ids:
                article = await self.get(similar_id)
                if article:
                    similar_articles.append(article)

            return similar_articles

        except Exception as e:
            logger.error(f"Failed to find similar articles: {str(e)}")
            raise StorageError(f"Failed to find similar articles: {str(e)}")

    async def get_by_author(self, author: str) -> List[Article]:
        """Get all articles by a specific author"""
        try:
            return await self.article_storage.find_by_author(author)

        except Exception as e:
            logger.error(f"Failed to get articles by author {author}: {str(e)}")
            raise StorageError(f"Failed to get articles by author: {str(e)}")

    async def get_by_source(self, source: str) -> List[Article]:
        """Get all articles from a specific source"""
        try:
            return await self.article_storage.find_by_source(source)

        except Exception as e:
            logger.error(f"Failed to get articles by source {source}: {str(e)}")
            raise StorageError(f"Failed to get articles by source: {str(e)}")
