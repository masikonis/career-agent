import pytest
import pytest_asyncio
from datetime import datetime
from src.storage.startup.store import StartupVectorStore
from src.storage.startup.models import Startup, StartupEvaluation, StartupIndustry, StartupStage

@pytest_asyncio.fixture
async def store():
    """Create a test store instance"""
    store = StartupVectorStore(persist_directory="./data/test_startups")
    yield store
    # Cleanup after tests
    await store.delete_item("test-ai-1")
    await store.delete_item("test-edu-1")

@pytest.mark.asyncio
async def test_startup_workflow(store):
    """Test complete startup workflow: add, search, evaluate, update"""

    # 1. Create test startups
    saas_startup = Startup(
        id="test-ai-1",
        name="AI SaaS",
        description="A SaaS platform for AI-powered analytics",
        industry=StartupIndustry.SAAS,
        stage=StartupStage.MVP
    )

    edtech_startup = Startup(
        id="test-edu-1",
        name="EdTech Platform",
        description="An educational technology platform for online learning",
        industry=StartupIndustry.EDTECH,
        stage=StartupStage.SEED
    )

    # 2. Add startups to store
    await store.add_startup(saas_startup)
    await store.add_startup(edtech_startup)

    # 3. Retrieve and verify
    retrieved_saas = await store.get_startup("test-ai-1")
    assert retrieved_saas is not None
    assert retrieved_saas.name == "AI SaaS"
    assert retrieved_saas.industry == StartupIndustry.SAAS
    assert retrieved_saas.stage == StartupStage.MVP

    # 4. Search by industry
    edtech_companies = await store.get_by_industry(StartupIndustry.EDTECH)
    assert len(edtech_companies) == 1
    assert edtech_companies[0].id == "test-edu-1"

    # 5. Find similar
    similar_startups = await store.find_similar_startups(
        "A platform for artificial intelligence and analytics"
    )
    assert len(similar_startups) > 0
    assert similar_startups[0].id == "test-ai-1"  # Most similar should be AI startup

    # 6. Add evaluation
    evaluation = StartupEvaluation(
        match_score=0.85,
        skills_match=["python", "saas"],
        notes="Good fit for SaaS expertise"
    )
    success = await store.add_evaluation("test-ai-1", evaluation)
    assert success is True

    # 7. Get evaluated startups
    evaluated = await store.get_evaluated_startups(min_score=0.8)
    assert len(evaluated) == 1
    assert evaluated[0].id == "test-ai-1"
    assert evaluated[0].evaluation is not None
    assert evaluated[0].evaluation.match_score == 0.85

    # 8. Get unevaluated startups
    unevaluated = await store.get_unevaluated_startups()
    assert len(unevaluated) == 1
    assert unevaluated[0].id == "test-edu-1"

    # 9. Get by stage
    mvp_startups = await store.get_by_stage(StartupStage.MVP)
    assert len(mvp_startups) == 1
    assert mvp_startups[0].id == "test-ai-1"
