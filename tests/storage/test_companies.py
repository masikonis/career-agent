from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from src.storage.companies import CompanyStorage
from src.storage.database import EntityNotFoundError, MongoDB, StorageError
from src.storage.models import Company, CompanyFilters, CompanyIndustry, CompanyStage
from src.utils.logger import get_logger

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def storage():
    # Reset MongoDB instance to ensure clean state
    await MongoDB.reset_instance()
    # Get storage instance with test flag
    db = await MongoDB.get_instance(is_test=True)
    storage = CompanyStorage(db)

    yield storage

    # Cleanup after tests
    await storage.collection.delete_many({})
    await MongoDB.reset_instance()


@pytest.mark.asyncio
async def test_company_storage_operations(storage):
    """Test complete company lifecycle including CRUD and search"""

    # 1. Create test companies
    company1 = Company(
        name="AI Testing Corp",
        description="Leading AI testing solutions",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
        website="https://aitesting.com",
        company_fit_score=0.85,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    company2 = Company(
        name="EdTech Solutions",
        description="Educational technology platform",
        industry=CompanyIndustry.EDTECH,
        stage=CompanyStage.SERIES_A,
        website="https://edtech.com",
        company_fit_score=0.75,
        created_at=datetime.now() - timedelta(days=30),
        updated_at=datetime.now(),
    )

    # Test Create
    company1_id = await storage.create(company1)
    company2_id = await storage.create(company2)
    assert company1_id is not None
    assert company2_id is not None

    # Test Read
    stored_company = await storage.get(company1_id)
    assert stored_company is not None
    assert stored_company.name == "AI Testing Corp"
    assert stored_company.industry == CompanyIndustry.SAAS
    assert stored_company.company_fit_score == 0.85

    # Test Update
    company1.description = "Updated AI testing solutions"
    success = await storage.update(company1_id, company1)
    assert success is True

    updated_company = await storage.get(company1_id)
    assert updated_company.description == "Updated AI testing solutions"

    # Test Search
    results = await storage.search(query="AI testing")
    assert len(results) == 1
    assert results[0].name == "AI Testing Corp"

    # Test Filters
    filters = CompanyFilters(
        industries=[CompanyIndustry.SAAS],
        stages=[CompanyStage.SEED],
        min_match_score=0.8,
    )
    filtered_results = await storage.search(filters=filters)
    assert len(filtered_results) == 1
    assert filtered_results[0].industry == CompanyIndustry.SAAS
    assert filtered_results[0].company_fit_score >= 0.8

    # Test Get All
    all_companies = await storage.get_all()
    assert len(all_companies) == 2

    # Test Delete
    success = await storage.delete(company1_id)
    assert success is True

    # Verify deletion
    remaining_companies = await storage.get_all()
    assert len(remaining_companies) == 1
    assert remaining_companies[0].id == company2_id


@pytest.mark.asyncio
async def test_crud_operations(storage):
    """Test all CRUD operations thoroughly"""
    logger.info("Starting CRUD operations test")

    # CREATE
    company = Company(
        name="Test Corp",
        description="Test company",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
        website="https://test.com",
    )
    logger.info(f"Creating test company: {company.name}")
    company_id = await storage.create(company)
    logger.info(f"Created company with ID: {company_id}")
    assert company_id is not None

    # READ
    logger.info(f"Reading company with ID: {company_id}")
    stored_company = await storage.get(company_id)
    logger.info(f"Retrieved company: {stored_company.name}")
    assert stored_company.name == "Test Corp"
    assert stored_company.industry == CompanyIndustry.SAAS
    assert stored_company.stage == CompanyStage.SEED

    # UPDATE
    stored_company.description = "Updated description"
    stored_company.stage = CompanyStage.SERIES_A
    logger.info(f"Updating company {company_id} with new description and stage")
    success = await storage.update(company_id, stored_company)
    assert success is True
    logger.info("Update successful")

    # Verify UPDATE
    updated_company = await storage.get(company_id)
    logger.info(f"Retrieved updated company: {updated_company.description}")
    assert updated_company.description == "Updated description"
    assert updated_company.stage == CompanyStage.SERIES_A
    assert updated_company.created_at == stored_company.created_at
    assert updated_company.updated_at > stored_company.updated_at

    # DELETE
    logger.info(f"Deleting company: {company_id}")
    success = await storage.delete(company_id)
    assert success is True
    logger.info("Delete successful")

    # Verify DELETE
    logger.info("Verifying deletion")
    with pytest.raises(EntityNotFoundError):
        await storage.get(company_id)
    logger.info("Deletion verified - company not found as expected")


@pytest.mark.asyncio
async def test_error_handling(storage):
    """Test error cases"""

    # Invalid ID format
    with pytest.raises(StorageError):
        await storage.get("invalid-id")

    # Non-existent ID
    with pytest.raises(EntityNotFoundError):
        await storage.get("507f1f77bcf86cd799439011")

    # Invalid website
    with pytest.raises(ValueError):
        Company(
            name="Invalid Corp",
            description="Test",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.SEED,
            website="not-a-url",
        )

    # Update non-existent company
    company = Company(
        name="Ghost Corp",
        description="Test",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
    )
    success = await storage.update("507f1f77bcf86cd799439011", company)
    assert success is False


@pytest.mark.asyncio
async def test_search_and_filters(storage):
    """Test search and filter functionality"""
    logger.info("Starting search and filters test")

    # Create test companies
    companies = [
        Company(
            name="AI Corp",
            description="AI company",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.SEED,
            website="https://ai.com",
        ),
        Company(
            name="EdTech Corp",
            description="Education company",
            industry=CompanyIndustry.EDTECH,
            stage=CompanyStage.SERIES_A,
            website="https://edtech.com",
        ),
    ]

    company_ids = []
    for company in companies:
        logger.info(f"Creating test company: {company.name}")
        company_id = await storage.create(company)
        company_ids.append(company_id)
        logger.info(f"Created company with ID: {company_id}")

    # Test text search
    logger.info("Testing text search for 'AI'")
    results = await storage.search(query="AI")
    assert len(results) == 1
    assert results[0].name == "AI Corp"
    logger.info(f"Found {len(results)} companies matching 'AI'")

    # Test industry filter
    logger.info("Testing industry filter for EDTECH")
    filters = CompanyFilters(industries=[CompanyIndustry.EDTECH])
    results = await storage.search(filters=filters)
    assert len(results) == 1
    assert results[0].industry == CompanyIndustry.EDTECH
    logger.info(f"Found {len(results)} companies in EDTECH industry")

    # Test stage filter
    logger.info("Testing stage filter for SEED stage")
    filters = CompanyFilters(stages=[CompanyStage.SEED])
    results = await storage.search(filters=filters)
    assert len(results) == 1
    assert results[0].stage == CompanyStage.SEED
    logger.info(f"Found {len(results)} companies in SEED stage")

    # Test combined filters
    logger.info("Testing combined industry and stage filters")
    filters = CompanyFilters(
        industries=[CompanyIndustry.SAAS, CompanyIndustry.EDTECH],
        stages=[CompanyStage.SERIES_A],
    )
    results = await storage.search(filters=filters)
    assert len(results) == 1
    assert results[0].name == "EdTech Corp"
    logger.info(f"Found {len(results)} companies matching combined filters")

    # Cleanup
    logger.info("Cleaning up test companies")
    for company_id in company_ids:
        await storage.delete(company_id)
    logger.info("Test companies deleted")
