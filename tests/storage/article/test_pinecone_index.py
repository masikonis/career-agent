import asyncio
from datetime import datetime

import pytest
import pytest_asyncio

from src.storage.article.pinecone_index import ArticlePineconeIndex
from src.storage.article.types import Article
from src.storage.base.types import EntityID
from src.utils.logger import get_logger

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def clean_test_env():
    """Setup and cleanup test environment"""
    # Create index with test namespace
    pinecone_index = ArticlePineconeIndex(namespace="test")

    # Cleanup before and after tests
    await pinecone_index.cleanup_namespace()

    yield

    await pinecone_index.cleanup_namespace()


@pytest.mark.asyncio
async def test_article_search(clean_test_env):
    """Test basic search functionality"""
    try:
        # Initialize components with test namespace
        pinecone_index = ArticlePineconeIndex(namespace="test")

        # Create a test article
        test_article = Article(
            title="Test Article",
            content="This is a test article about artificial intelligence and machine learning",
            author="Test Author",
            source="Test Source",
            published_at=datetime.now(),
            tags=["AI", "ML", "test"],
        )

        # Create metadata for indexing
        metadata = {
            "title": test_article.title,
            "author": test_article.author,
            "source": test_article.source,
            "tags": ",".join(test_article.tags),
            "published_at": test_article.published_at.isoformat(),
        }

        # Index the article
        article_id = EntityID("test123")
        success = await pinecone_index.index(article_id, test_article, metadata)
        assert success
        logger.info("✓ Successfully indexed test article")

        # Wait for indexing
        await asyncio.sleep(4)

        # Search for it
        results = await pinecone_index.search("artificial intelligence", limit=1)
        assert len(results) > 0
        assert results[0] == article_id
        logger.info("✓ Successfully found test article in search")

        # Clean up
        success = await pinecone_index.delete_from_index(article_id)
        assert success
        logger.info("✓ Successfully cleaned up test article")

    except Exception as e:
        logger.error(f"Article search test failed: {str(e)}")
        raise
