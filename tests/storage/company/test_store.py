import pytest
import pytest_asyncio
from datetime import datetime
from src.storage.company.store import CompanyVectorStore
from src.storage.company.models import Company, CompanyStage, CompanyIndustry, CompanyEvaluation
from src.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)

@pytest_asyncio.fixture
async def store():
    """Create a test store instance"""
    store = CompanyVectorStore(namespace="test")
    
    # Clean up before test
    try:
        await store.delete_item("test-ai-1")
        await store.delete_item("test-edu-1")
        logger.info("Cleaned up any existing test data")
    except Exception as e:
        logger.warning(f"Pre-test cleanup error (can be ignored): {e}")
    
    yield store

    # Clean up after test
    try:
        await store.delete_item("test-ai-1")
        await store.delete_item("test-edu-1")
        logger.info("Test data cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")

@pytest.mark.asyncio
async def test_basic_operations(store):
    """Test basic company operations: add, get, find similar"""
    
    # 1. Create test company
    saas_company = Company(
        id="test-ai-1",
        name="AI SaaS",
        description="A SaaS platform for AI-powered analytics",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.MVP
    )
    logger.debug(f"Created test company: {saas_company.to_dict()}")

    # 2. Add company to store
    await store.add_company(saas_company)
    logger.info("Added company to store")

    # 3. Retrieve and verify
    retrieved_saas = await store.get_company("test-ai-1")
    assert retrieved_saas is not None
    assert retrieved_saas.name == "AI SaaS"
    assert retrieved_saas.industry == CompanyIndustry.SAAS
    assert retrieved_saas.stage == CompanyStage.MVP

@pytest.mark.asyncio
async def test_multiple_startups(store):
    """Test handling multiple startups"""
    
    # 1. Create test startups
    startups = [
        Company(
            id="test-ai-1",
            name="AI SaaS",
            description="A SaaS platform for AI-powered analytics",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.MVP
        ),
        Company(
            id="test-edu-1",
            name="EdTech Platform",
            description="An educational technology platform for online learning",
            industry=CompanyIndustry.EDTECH,
            stage=CompanyStage.SEED
        )
    ]

    # 2. Add startups to store with verification
    for startup in startups:
        await store.add_company(startup)
        await asyncio.sleep(2)  # Wait between adds
        
        # Verify immediately after add
        retrieved = await store.get_company(startup.id)
        assert retrieved is not None, f"Failed to verify startup {startup.id} after add"
        assert retrieved.name == startup.name
        assert retrieved.description == startup.description

@pytest.mark.asyncio
async def test_update_startup(store):
    """Test updating startup information"""
    logger.info("Starting update startup test")
    
    # 1. Create and add startup
    startup = Company(
        id="test-ai-1",
        name="AI SaaS",
        description="Initial description",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.MVP
    )
    logger.debug(f"Created initial startup: {startup.to_dict()}")
    
    await store.add_company(startup)
    await asyncio.sleep(2)

    # Verify initial state
    initial = await store.get_company(startup.id)
    logger.debug(f"Initial state verification: {initial.to_dict() if initial else None}")
    assert initial is not None
    assert initial.description == "Initial description"

    # 2. Update startup
    startup.description = "Updated description"
    logger.debug(f"Updating startup with new data: {startup.to_dict()}")
    success = await store.update_company(startup)
    assert success is True
    await asyncio.sleep(2)

    # 3. Verify update with retries
    max_retries = 3
    for i in range(max_retries):
        updated = await store.get_company(startup.id)
        logger.debug(f"Update verification attempt {i+1}, got: {updated.to_dict() if updated else None}")
        
        if updated and updated.description == "Updated description":
            logger.info("Update verification successful")
            break
            
        logger.debug(f"Attempt {i+1} failed, waiting before retry...")
        await asyncio.sleep(2)
    else:
        assert False, "Failed to verify update after multiple retries"

    assert updated is not None
    assert updated.description == "Updated description"
