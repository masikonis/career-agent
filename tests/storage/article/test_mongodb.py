import asyncio
from datetime import datetime, timedelta
from typing import List

import pytest
import pytest_asyncio

from src.config import config
from src.storage.article.mongodb import ArticleMongoDBStorage
from src.storage.article.types import Article
from src.storage.base.types import EntityID
from src.utils.logger import get_logger

logger = get_logger("article.test_mongodb")


@pytest_asyncio.fixture
async def clean_test_env():
    """Setup and cleanup test environment"""
    # Create storage with test flag
    mongo_storage = ArticleMongoDBStorage(
        connection_string=config["MONGODB_URI"],
        database=f"{config['MONGODB_DB_NAME']}-test",
        is_test=True,
    )

    # Cleanup before and after tests
    await mongo_storage.cleanup_test_data()
    yield mongo_storage  # Return the storage instance
    await mongo_storage.cleanup_test_data()


@pytest.mark.asyncio
async def test_article_crud(clean_test_env: ArticleMongoDBStorage):
    """Test basic CRUD operations"""
    try:
        mongo_storage = clean_test_env  # Use the fixture instance

        # Create test article
        article = Article(
            title="Test Article",
            content="Test content",
            author="Test Author",
            source="Test Source",
            published_at=datetime.now(),
            tags=["test", "article"],
        )

        # Create
        article_id = await mongo_storage.create(article)
        assert article_id is not None
        logger.info(f"✓ Created test article with ID: {article_id}")

        # Read
        stored_article = await mongo_storage.get(article_id)
        assert stored_article is not None
        assert stored_article.title == article.title
        assert stored_article.content == article.content
        logger.info("✓ Retrieved test article")

        # Update
        article.title = "Updated Title"
        success = await mongo_storage.update(article_id, article)
        assert success
        updated_article = await mongo_storage.get(article_id)
        assert updated_article.title == "Updated Title"
        logger.info("✓ Updated test article")

        # Delete
        success = await mongo_storage.delete(article_id)
        assert success
        deleted_article = await mongo_storage.get(article_id)
        assert deleted_article is None
        logger.info("✓ Deleted test article")

    except Exception as e:
        logger.error(f"Article CRUD test failed: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_article_tags(clean_test_env: ArticleMongoDBStorage):
    """Test tag operations"""
    try:
        mongo_storage = clean_test_env  # Use the fixture instance

        # Create article with initial tags
        article = Article(
            title="Test Article",
            content="Test content",
            author="Test Author",
            source="Test Source",
            published_at=datetime.now(),
            tags=["initial"],
        )
        article_id = await mongo_storage.create(article)

        # Add tags
        new_tags = ["tag1", "tag2"]
        success = await mongo_storage.add_tags(article_id, new_tags)
        assert success

        updated_article = await mongo_storage.get(article_id)
        assert all(tag in updated_article.tags for tag in new_tags)
        logger.info("✓ Added tags successfully")

        # Remove tags
        success = await mongo_storage.remove_tags(article_id, ["tag1"])
        assert success

        updated_article = await mongo_storage.get(article_id)
        assert "tag1" not in updated_article.tags
        assert "tag2" in updated_article.tags
        logger.info("✓ Removed tags successfully")

    except Exception as e:
        logger.error(f"Article tags test failed: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_article_queries(clean_test_env: ArticleMongoDBStorage):
    """Test article queries"""
    try:
        mongo_storage = clean_test_env  # Use the fixture instance

        # Create test articles
        now = datetime.now()
        articles = [
            Article(
                title=f"Article {i}",
                content=f"Content {i}",
                author="Author A" if i % 2 == 0 else "Author B",
                source="Source X" if i < 2 else "Source Y",
                published_at=now - timedelta(days=i),
                tags=["tag1"] if i % 2 == 0 else ["tag2"],
            )
            for i in range(4)
        ]

        article_ids: List[EntityID] = []
        for article in articles:
            article_id = await mongo_storage.create(article)
            article_ids.append(article_id)

        # Test date range query
        date_range_articles = await mongo_storage.find_by_date_range(
            now - timedelta(days=2), now
        )
        assert len(date_range_articles) == 3
        logger.info("✓ Date range query successful")

        # Test list with filters
        filtered_articles = await mongo_storage.list(
            {
                "author": "Author A",
                "source": "Source X",
                "tags": ["tag1"],
                "published_after": now - timedelta(days=3),
                "published_before": now,
            }
        )
        assert len(filtered_articles) > 0
        logger.info("✓ Filtered list query successful")

    except Exception as e:
        logger.error(f"Article queries test failed: {str(e)}")
        raise
