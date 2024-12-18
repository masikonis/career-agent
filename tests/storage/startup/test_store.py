import pytest
import pytest_asyncio
from datetime import datetime
from src.storage.startup.store import StartupVectorStore
from src.storage.startup.models import Startup, StartupEvaluation, StartupIndustry, StartupStage
from src.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)

@pytest_asyncio.fixture
async def store():
    """Create a test store instance"""
    store = StartupVectorStore(namespace="test")
    logger.info(f"Created test store with namespace: {store.namespace}")
    
    # Clean up before test (in case previous test failed)
    try:
        await store.delete_item("test-ai-1")
        await store.delete_item("test-edu-1")
        logger.info("Cleaned up any existing test data")
    except Exception as e:
        logger.warning(f"Pre-test cleanup error (can be ignored): {e}")
    
    yield store
    
    # Cleanup after tests
    try:
        await store.delete_item("test-ai-1")
        await store.delete_item("test-edu-1")
        logger.info("Test data cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")

@pytest.mark.asyncio
async def test_basic_operations(store):
    """Test basic startup operations: add, get, find similar"""
    logger.info("Starting basic operations test")
    
    # 1. Create test startup
    saas_startup = Startup(
        id="test-ai-1",
        name="AI SaaS",
        description="A SaaS platform for AI-powered analytics",
        industry=StartupIndustry.SAAS,
        stage=StartupStage.MVP
    )
    logger.debug(f"Created test startup: {saas_startup.to_dict()}")

    # 2. Add startup to store
    await store.add_startup(saas_startup)
    logger.info("Added startup to store")

    # 3. Retrieve and verify
    retrieved_saas = await store.get_startup("test-ai-1")
    assert retrieved_saas is not None
    assert retrieved_saas.name == "AI SaaS"
    assert retrieved_saas.industry == StartupIndustry.SAAS
    assert retrieved_saas.stage == StartupStage.MVP

    # 4. Find similar startups
    similar_results = await store.find_similar(
        "A platform for artificial intelligence and analytics",
        n_results=1
    )
    assert len(similar_results) > 0
    assert similar_results[0]['id'] == "test-ai-1"

@pytest.mark.asyncio
async def test_multiple_startups(store):
    """Test handling multiple startups"""
    
    # 1. Create test startups
    startups = [
        Startup(
            id="test-ai-1",
            name="AI SaaS",
            description="A SaaS platform for AI-powered analytics",
            industry=StartupIndustry.SAAS,
            stage=StartupStage.MVP
        ),
        Startup(
            id="test-edu-1",
            name="EdTech Platform",
            description="An educational technology platform for online learning",
            industry=StartupIndustry.EDTECH,
            stage=StartupStage.SEED
        )
    ]

    # 2. Add startups to store with verification
    for startup in startups:
        await store.add_startup(startup)
        await asyncio.sleep(2)  # Wait between adds
        
        # Verify immediately after add
        retrieved = await store.get_startup(startup.id)
        assert retrieved is not None, f"Failed to verify startup {startup.id} after add"
        assert retrieved.name == startup.name
        assert retrieved.description == startup.description

@pytest.mark.asyncio
async def test_update_startup(store):
    """Test updating startup information"""
    logger.info("Starting update startup test")
    
    # 1. Create and add startup
    startup = Startup(
        id="test-ai-1",
        name="AI SaaS",
        description="Initial description",
        industry=StartupIndustry.SAAS,
        stage=StartupStage.MVP
    )
    logger.debug(f"Created initial startup: {startup.to_dict()}")
    
    await store.add_startup(startup)
    await asyncio.sleep(2)

    # Verify initial state
    initial = await store.get_startup(startup.id)
    logger.debug(f"Initial state verification: {initial.to_dict() if initial else None}")
    assert initial is not None
    assert initial.description == "Initial description"

    # 2. Update startup
    startup.description = "Updated description"
    logger.debug(f"Updating startup with new data: {startup.to_dict()}")
    success = await store.update_startup(startup)
    assert success is True
    await asyncio.sleep(2)

    # 3. Verify update with retries
    max_retries = 3
    for i in range(max_retries):
        updated = await store.get_startup(startup.id)
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
