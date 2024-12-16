import pytest
from src.storage.vector_store import StartupVectorStore
import tempfile
import shutil
import os
from pytest_asyncio import fixture

@fixture
async def vector_store():
    # Create temporary directory for test database
    test_dir = tempfile.mkdtemp()
    store = StartupVectorStore(persist_directory=test_dir)
    yield store
    # Cleanup
    shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_add_and_retrieve_startup(vector_store):
    startup_id = "test123"
    name = "Test Startup"
    description = "An AI company doing amazing things"
    metadata = {
        "industry": "AI",
        "funding": "Seed"
    }

    # Add startup
    await vector_store.add_startup(startup_id, name, description, metadata)

    # Retrieve startup
    startup = await vector_store.get_startup(startup_id)
    
    assert startup is not None
    assert startup['metadata']['name'] == name
    assert startup['metadata']['industry'] == "AI"
    assert not startup['metadata']['evaluated']

@pytest.mark.asyncio
async def test_evaluation_workflow(vector_store):
    # Add startup
    await vector_store.add_startup(
        "test456",
        "Another Startup",
        "A blockchain company",
        {"industry": "Blockchain"}
    )

    # Mark as evaluated
    evaluation = {"match_score": 0.8, "skills_match": ["python", "blockchain"]}
    await vector_store.mark_as_evaluated("test456", evaluation)

    # Check if properly marked
    startup = await vector_store.get_startup("test456")
    assert startup['metadata']['evaluated']
    assert "evaluation_result" in startup['metadata'] 