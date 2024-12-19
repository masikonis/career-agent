from datetime import datetime

import pytest

from src.config import config
from src.storage.company.mongodb import MongoDBCompanyStorage
from src.storage.company.types import Company, CompanyIndustry, CompanyStage
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_mongodb_connection():
    """Simple test to verify MongoDB connection and basic operations"""
    try:
        # Initialize storage with config from environment
        storage = MongoDBCompanyStorage(config)
        logger.info("✓ Successfully connected to MongoDB")

        # Create a test company
        test_company = Company(
            id=None,
            name="Test Company",
            description="A test company for MongoDB connection",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.SEED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Try to store it
        doc = storage._to_document(test_company)
        result = storage.companies.insert_one(doc)
        logger.info(
            f"✓ Successfully inserted test company with ID: {result.inserted_id}"
        )

        # Verify we can read it back
        found_doc = storage.companies.find_one({"_id": result.inserted_id})
        if found_doc:
            logger.info(f"✓ Successfully retrieved test company: {found_doc['name']}")
        else:
            raise Exception("Failed to retrieve test company")

        # Clean up
        delete_result = storage.companies.delete_one({"_id": result.inserted_id})
        if delete_result.deleted_count > 0:
            logger.info("✓ Successfully cleaned up test company")
        else:
            logger.warning("Failed to clean up test company")

    except Exception as e:
        logger.error(f"MongoDB connection test failed: {str(e)}")
        raise
