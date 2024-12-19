from datetime import datetime

import pytest

from src.config import config
from src.storage.base.types import Metadata
from src.storage.company.pinecone_index import PineconeCompanyIndex
from src.storage.company.types import Company, CompanyIndustry, CompanyStage
from src.utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.asyncio  # Mark the test as async
async def test_pinecone_connection():
    """Simple test to verify Pinecone connection and basic operations"""
    try:
        # Initialize search index with test namespace
        search_index = PineconeCompanyIndex(namespace="test")
        logger.info("✓ Successfully connected to Pinecone")

        # Create a test company
        test_company = Company(
            id="test123",  # Using fixed ID for test
            name="Test Company",
            description="An innovative SaaS company focused on AI solutions",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.SEED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create metadata for indexing
        metadata = {
            "name": test_company.name,
            "industry": test_company.industry.value,
            "stage": test_company.stage.value,
        }

        # Try to index it
        success = await search_index.index(test_company.id, test_company, metadata)
        assert success
        logger.info("✓ Successfully indexed test company")

        # Try to search for it
        results = await search_index.search("SaaS AI company", limit=1)
        assert len(results) > 0
        assert results[0] == test_company.id
        logger.info("✓ Successfully found test company in search")

        # Clean up
        success = await search_index.delete_from_index(test_company.id)
        assert success
        logger.info("✓ Successfully cleaned up test company")

    except Exception as e:
        logger.error(f"Pinecone connection test failed: {str(e)}")
        raise
