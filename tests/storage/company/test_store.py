import asyncio
from datetime import datetime

import pytest
import pytest_asyncio

from src.storage.company.models import (
    Company,
    CompanyEvaluation,
    CompanyIndustry,
    CompanyStage,
)
from src.storage.company.store import CompanyVectorStore
from src.utils.logger import get_logger

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
    
    # 1. Create test company with initial evaluation
    initial_evaluation = CompanyEvaluation(
        match_score=85.5,
        skills_match=["Python", "Machine Learning"],
        notes="Strong alignment with current skills."
    )
    saas_company = Company(
        id="test-ai-1",
        name="AI SaaS",
        description="A SaaS platform for AI-powered analytics",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.MVP,
        evaluations=[initial_evaluation]
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
    assert len(retrieved_saas.evaluations) == 1
    assert retrieved_saas.evaluations[0].match_score == 85.5

    # 4. Add a new evaluation
    new_evaluation = CompanyEvaluation(
        match_score=90.0,
        skills_match=["Python", "Deep Learning"],
        notes="Skills have improved over the year."
    )
    retrieved_saas.add_evaluation(new_evaluation)
    await store.update_company(retrieved_saas)
    logger.info("Added a new evaluation to the company")

    # 5. Retrieve and verify the new evaluation
    updated_saas = await store.get_company("test-ai-1")
    assert updated_saas is not None
    assert len(updated_saas.evaluations) == 2
    assert updated_saas.evaluations[1].match_score == 90.0

@pytest.mark.asyncio
async def test_multiple_evaluations(store):
    """Test adding multiple evaluations over time"""
    
    # 1. Create test company
    company = Company(
        id="test-edu-1",
        name="EdTech Platform",
        description="An educational technology platform for online learning",
        industry=CompanyIndustry.EDTECH,
        stage=CompanyStage.SEED
    )
    logger.debug(f"Created test company: {company.to_dict()}")

    # 2. Add company to store without evaluations
    await store.add_company(company)
    logger.info("Added company to store without evaluations")

    # 3. Add first evaluation
    first_evaluation = CompanyEvaluation(
        match_score=75.0,
        skills_match=["Educational Content", "User Engagement"],
        notes="Initial evaluation."
    )
    company.add_evaluation(first_evaluation)
    await store.update_company(company)
    logger.info("Added first evaluation")

    # 4. Add second evaluation after some time
    await asyncio.sleep(1)  # Simulate time passing
    second_evaluation = CompanyEvaluation(
        match_score=80.0,
        skills_match=["Content Development", "Analytics"],
        notes="Skills have been updated."
    )
    company.add_evaluation(second_evaluation)
    await store.update_company(company)
    logger.info("Added second evaluation")

    # 5. Retrieve and verify both evaluations
    retrieved_company = await store.get_company("test-edu-1")
    assert retrieved_company is not None
    assert len(retrieved_company.evaluations) == 2
    assert retrieved_company.evaluations[0].match_score == 75.0
    assert retrieved_company.evaluations[1].match_score == 80.0
