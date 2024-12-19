from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from src.utils.logger import get_logger

from ..base.exceptions import StorageError
from ..base.types import EntityID
from ..generic.mongodb import MongoDBStorage, MongoOperators
from .interfaces import ArticleStorage
from .types import Article


class ArticleMongoDBStorage(MongoDBStorage[Article], ArticleStorage):
    """MongoDB storage implementation for articles"""

    # Class constants for collection fields
    FIELD_AUTHOR: ClassVar[str] = "author"
    FIELD_SOURCE: ClassVar[str] = "source"
    FIELD_PUBLISHED_AT: ClassVar[str] = "published_at"
    FIELD_TAGS: ClassVar[str] = "tags"
    FIELD_CREATED_AT: ClassVar[str] = "created_at"
    FIELD_TITLE: ClassVar[str] = "title"
    FIELD_CONTENT: ClassVar[str] = "content"

    def __init__(self, connection_string: str, database: str, is_test: bool = False):
        super().__init__(
            connection_string=connection_string,
            database=database,
            collection="articles",
            is_test=is_test,
        )
        self.logger = get_logger(__name__)

        # Create indexes
        self._create_indexes()

    def _create_indexes(self) -> None:
        """Create MongoDB indexes for efficient querying"""
        try:
            # Create indexes for common queries
            self.collection.create_index([(self.FIELD_AUTHOR, ASCENDING)])
            self.collection.create_index([(self.FIELD_SOURCE, ASCENDING)])
            self.collection.create_index([(self.FIELD_PUBLISHED_AT, DESCENDING)])
            self.collection.create_index([(self.FIELD_TAGS, ASCENDING)])
            self.collection.create_index([(self.FIELD_CREATED_AT, DESCENDING)])

            # Create text index for basic text search
            self.collection.create_index(
                [(self.FIELD_TITLE, "text"), (self.FIELD_CONTENT, "text")]
            )

            self.logger.info("Created MongoDB indexes for articles collection")

        except Exception as e:
            self.logger.error(f"Failed to create indexes: {str(e)}")
            raise StorageError(f"Failed to create indexes: {str(e)}")

    async def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Article]:
        """Find articles within a date range"""
        try:
            cursor = self.collection.find(
                {
                    self.FIELD_PUBLISHED_AT: {
                        MongoOperators.GTE: start_date,
                        MongoOperators.LTE: end_date,
                    }
                }
            ).sort(self.FIELD_PUBLISHED_AT, DESCENDING)

            articles = []
            async for doc in cursor:
                articles.append(Article.from_dict(doc))

            return articles

        except Exception as e:
            self.logger.error(f"Failed to find articles by date range: {str(e)}")
            raise StorageError(f"Failed to find articles by date range: {str(e)}")

    async def add_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        """Add tags to an article"""
        try:
            # Add tags without duplicates
            result = await self.collection.update_one(
                {"_id": ObjectId(article_id)},
                {
                    MongoOperators.ADD_TO_SET: {
                        self.FIELD_TAGS: {MongoOperators.EACH: tags}
                    }
                },
            )

            if result.matched_count == 0:
                self.logger.warning(f"Article {article_id} not found")
                return False

            self.logger.info(f"Added tags to article {article_id}: {tags}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add tags: {str(e)}")
            raise StorageError(f"Failed to add tags: {str(e)}")

    async def remove_tags(self, article_id: EntityID, tags: List[str]) -> bool:
        """Remove tags from an article"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(article_id)},
                {MongoOperators.PULL_ALL: {self.FIELD_TAGS: tags}},
            )

            if result.matched_count == 0:
                self.logger.warning(f"Article {article_id} not found")
                return False

            self.logger.info(f"Removed tags from article {article_id}: {tags}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove tags: {str(e)}")
            raise StorageError(f"Failed to remove tags: {str(e)}")

    async def list(
        self, filter_params: Optional[Dict[str, Any]] = None
    ) -> List[Article]:
        """List articles with optional filtering"""
        try:
            # Build query from filter params
            query: Dict[str, Any] = {}
            if filter_params:
                if self.FIELD_AUTHOR in filter_params:
                    query[self.FIELD_AUTHOR] = filter_params[self.FIELD_AUTHOR]
                if self.FIELD_SOURCE in filter_params:
                    query[self.FIELD_SOURCE] = filter_params[self.FIELD_SOURCE]
                if self.FIELD_TAGS in filter_params:
                    query[self.FIELD_TAGS] = {
                        MongoOperators.ALL: filter_params[self.FIELD_TAGS]
                    }
                if "published_after" in filter_params:
                    query.setdefault(self.FIELD_PUBLISHED_AT, {})
                    query[self.FIELD_PUBLISHED_AT][MongoOperators.GTE] = filter_params[
                        "published_after"
                    ]
                if "published_before" in filter_params:
                    query.setdefault(self.FIELD_PUBLISHED_AT, {})
                    query[self.FIELD_PUBLISHED_AT][MongoOperators.LTE] = filter_params[
                        "published_before"
                    ]

            # Execute query
            cursor = self.collection.find(query).sort(
                self.FIELD_PUBLISHED_AT, DESCENDING
            )
            articles = []

            async for doc in cursor:
                articles.append(Article.from_dict(doc))

            return articles

        except Exception as e:
            self.logger.error(f"Failed to list articles: {str(e)}")
            raise StorageError(f"Failed to list articles: {str(e)}")
