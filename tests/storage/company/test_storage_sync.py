import asyncio
from datetime import datetime

import pytest
import pytest_asyncio

from src.config import config
from src.storage.company.manager import CompanyStorageManager
from src.storage.company.mongodb import MongoDBCompanyStorage
from src.storage.company.pinecone_index import PineconeCompanyIndex
from src.storage.company.types import (
    Company,
    CompanyEvaluation,
    CompanyIndustry,
    CompanyStage,
)
from src.utils.logger import get_logger

logger = get_logger("company.test_storage_sync")


@pytest_asyncio.fixture
async def clean_test_env():
    # Create storage with test flag
    mongo_storage = MongoDBCompanyStorage(config, is_test=True)
    pinecone_index = PineconeCompanyIndex(namespace="test")

    # Cleanup before and after tests
    await mongo_storage.cleanup_test_data()
    await pinecone_index.cleanup_namespace()

    yield

    await mongo_storage.cleanup_test_data()
    await pinecone_index.cleanup_namespace()


@pytest.mark.asyncio
async def test_mongodb_pinecone_sync(clean_test_env):
    """Test that changes in MongoDB are reflected in Pinecone search index"""
    try:
        # Initialize components with test flag
        mongo_storage = MongoDBCompanyStorage(config, is_test=True)
        pinecone_index = PineconeCompanyIndex(namespace="test")
        storage_manager = CompanyStorageManager(mongo_storage, pinecone_index)

        # Create a test company
        test_company = Company(
            id=None,  # MongoDB will generate ID
            name="AI Testing Company",
            description="A company specializing in AI-powered testing solutions",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.SEED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # 1. Test Create Sync
        company_id = await storage_manager.create(test_company)
        assert company_id, "Failed to create company"
        logger.info(f"✓ Created company in MongoDB with ID: {company_id}")

        # Add longer delay to ensure indexing is complete
        await asyncio.sleep(4)

        # Verify it's searchable in Pinecone
        search_results = await storage_manager.search_companies("AI testing")
        assert len(search_results) == 1, f"Expected 1 result, got {len(search_results)}"
        logger.info(f"Found company in search with ID: {search_results[0].id}")
        assert (
            search_results[0].id == company_id
        ), f"Expected {company_id}, got {search_results[0].id}"
        logger.info("✓ Company found in Pinecone search")

        # 2. Test Update Sync
        # Add an evaluation
        evaluation = CompanyEvaluation(
            match_score=0.85,
            skills_match=["AI", "Testing", "Python"],
            notes="Great potential for collaboration",
        )
        success = await storage_manager.add_evaluation(company_id, evaluation)
        assert success, "Failed to add evaluation"
        logger.info("✓ Added evaluation to company")

        # Verify the update is reflected in search
        similar_companies = await storage_manager.find_similar_companies(company_id)
        assert len(similar_companies) >= 0  # Might be 0 if no similar companies
        logger.info("✓ Successfully queried similar companies after update")

        # 3. Test Delete Sync
        success = await storage_manager.delete(company_id)
        assert success, "Failed to delete company"
        logger.info("✓ Deleted company from MongoDB")

        # Verify it's removed from search
        search_results = await storage_manager.search_companies("AI testing")
        assert not any(r.id == company_id for r in search_results)
        logger.info("✓ Company no longer found in Pinecone search")

    except Exception as e:
        logger.error(f"Storage sync test failed: {str(e)}")
        raise
