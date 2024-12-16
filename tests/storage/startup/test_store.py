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
    await store.delete_item("test-fin-1")

@pytest.mark.asyncio
async def test_startup_workflow(store):
    """Test complete startup workflow: add, search, evaluate, update"""

    # 1. Create test startups
    ai_startup = Startup(
        id="test-ai-1",
        name="AI Tech",
        description="An AI company focusing on machine learning solutions",
        industry=StartupIndustry.AI,
        stage=StartupStage.SEED,
        tech_stack=["python", "tensorflow", "aws"],
        team_size=10
    )

    fintech_startup = Startup(
        id="test-fin-1",
        name="FinTech Solutions",
        description="A fintech company working on payment solutions",
        industry=StartupIndustry.FINTECH,
        stage=StartupStage.SERIES_A,
        tech_stack=["java", "postgresql", "kubernetes"],
        team_size=25
    )

    # 2. Add startups to store
    await store.add_startup(ai_startup)
    await store.add_startup(fintech_startup)

    # 3. Retrieve and verify
    retrieved_ai = await store.get_startup("test-ai-1")
    assert retrieved_ai is not None
    assert retrieved_ai.name == "AI Tech"
    assert retrieved_ai.industry == StartupIndustry.AI

    # 4. Search by industry
    ai_companies = await store.get_by_industry(StartupIndustry.AI)
    assert len(ai_companies) == 1
    assert ai_companies[0].id == "test-ai-1"

    # 5. Search by tech stack
    python_companies = await store.get_by_tech_stack("python")
    assert len(python_companies) == 1
    assert python_companies[0].id == "test-ai-1"

    # 6. Find similar
    similar_startups = await store.find_similar_startups(
        "A company working on AI and machine learning"
    )
    assert len(similar_startups) > 0
    assert similar_startups[0].id == "test-ai-1"  # Most similar should be AI startup

    # 7. Add evaluation
    evaluation = StartupEvaluation(
        match_score=0.85,
        skills_match=["python", "machine learning"],
        notes="Good fit for AI expertise"
    )
    success = await store.add_evaluation("test-ai-1", evaluation)
    assert success is True

    # 8. Get evaluated startups
    evaluated = await store.get_evaluated_startups(min_score=0.8)
    assert len(evaluated) == 1
    assert evaluated[0].id == "test-ai-1"
    assert evaluated[0].evaluation is not None
    assert evaluated[0].evaluation.match_score == 0.85

    # 9. Get unevaluated startups
    unevaluated = await store.get_unevaluated_startups()
    assert len(unevaluated) == 1
    assert unevaluated[0].id == "test-fin-1"

    # 10. Update startup
    ai_startup.team_size = 15
    success = await store.update_startup(ai_startup)
    assert success is True

    updated = await store.get_startup("test-ai-1")
    assert updated is not None
    assert updated.team_size == 15
