from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from src.repositories.database import EntityNotFoundError, MongoDB, RepositoryError
from src.repositories.jobs import JobRepository
from src.repositories.models import JobAd
from src.utils.logger import get_logger

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def repository():
    """Create a test storage instance with proper test database"""
    # Reset MongoDB instance to ensure clean state
    await MongoDB.reset_instance()

    # Get storage instance with test flag
    db = await MongoDB.get_instance(is_test=True)
    repository = JobRepository(db)

    # Ensure we're using test database
    assert "test" in repository.db.db.name.lower(), "Not using test database!"

    yield repository

    # Cleanup after tests
    await repository.collection.delete_many({})
    await MongoDB.reset_instance()


@pytest.mark.asyncio
async def test_job_repository_operations(repository):
    """Test complete job lifecycle including CRUD and evaluation"""

    # 1. Create test jobs
    job1 = JobAd(
        company_id="company123",
        title="Senior Python Developer",
        description="Leading Python development role",
        requirements=["Python", "FastAPI", "MongoDB"],
        salary_range=(80000, 120000),
        active=True,
    )

    job2 = JobAd(
        company_id="company456",
        title="ML Engineer",
        description="Machine learning role",
        requirements=["Python", "TensorFlow", "PyTorch"],
        salary_range=(90000, 130000),
        active=True,
    )

    # Test Create
    job1_id = await repository.create(job1)
    job2_id = await repository.create(job2)
    assert job1_id is not None
    assert job2_id is not None

    # Test Read
    stored_job = await repository.get(job1_id)
    assert stored_job is not None
    assert stored_job.title == "Senior Python Developer"
    assert stored_job.requirements == ["Python", "FastAPI", "MongoDB"]

    # Test Evaluation
    success = await repository.update_evaluation(
        job1_id,
        match_score=0.85,
        skills_match=["Python", "FastAPI"],
        notes="Good match for Python skills",
    )
    assert success is True

    evaluated_job = await repository.get(job1_id)
    assert evaluated_job.match_score == 0.85
    assert evaluated_job.skills_match == ["Python", "FastAPI"]
    assert evaluated_job.evaluation_notes == "Good match for Python skills"
    assert evaluated_job.evaluated_at is not None

    # Test Get Company Jobs
    company_jobs = await repository.get_company_jobs("company123")
    assert len(company_jobs) == 1
    assert company_jobs[0].title == "Senior Python Developer"

    # Test Best Matches
    await repository.update_evaluation(
        job2_id,
        match_score=0.95,
        skills_match=["Python"],
        notes="Excellent ML opportunity",
    )

    best_matches = await repository.get_best_matches(min_score=0.8)
    assert len(best_matches) == 2
    assert best_matches[0].match_score >= best_matches[1].match_score  # Sorted by score

    # Test Archive
    success = await repository.archive_job(job1_id)
    assert success is True

    # Verify archived job not in active jobs
    active_jobs = await repository.get_company_jobs(
        "company123", include_archived=False
    )
    assert len(active_jobs) == 0

    # But should be in all jobs
    all_jobs = await repository.get_company_jobs("company123", include_archived=True)
    assert len(all_jobs) == 1


@pytest.mark.asyncio
async def test_error_handling(repository):
    """Test error cases"""

    # Invalid ID format
    with pytest.raises(RepositoryError):
        await repository.get("invalid-id")

    # Non-existent ID
    with pytest.raises(EntityNotFoundError):
        await repository.get("507f1f77bcf86cd799439011")

    # Invalid evaluation score
    job = JobAd(
        company_id="company123",
        title="Test Job",
        description="Test description",
        requirements=["Python"],
    )
    job_id = await repository.create(job)

    with pytest.raises(ValueError):
        await repository.update_evaluation(
            job_id,
            match_score=1.5,  # Should be between 0 and 1
            skills_match=["Python"],
            notes="Test",
        )


@pytest.mark.asyncio
async def test_job_lifecycle(repository):
    """Test job lifecycle with evaluations and archiving"""

    # Create job
    job = JobAd(
        company_id="company123",
        title="Software Engineer",
        description="Engineering role",
        requirements=["Python", "JavaScript"],
        active=True,
    )

    job_id = await repository.create(job)

    # Initial evaluation
    await repository.update_evaluation(
        job_id, match_score=0.7, skills_match=["Python"], notes="Initial evaluation"
    )

    # Re-evaluate
    await repository.update_evaluation(
        job_id,
        match_score=0.8,
        skills_match=["Python", "JavaScript"],
        notes="Updated evaluation",
    )

    stored_job = await repository.get(job_id)
    assert stored_job.match_score == 0.8
    assert len(stored_job.skills_match) == 2

    # Archive
    await repository.archive_job(job_id)
    archived_job = await repository.get(job_id)
    assert archived_job.active is False
    assert archived_job.archived_at is not None


@pytest.mark.asyncio
async def test_cleanup(repository):
    """Test cleanup functionality"""

    # Create test jobs
    jobs = [
        JobAd(
            company_id=f"company{i}",
            title=f"Job {i}",
            description=f"Description {i}",
            requirements=["Python"],
        )
        for i in range(3)
    ]

    for job in jobs:
        await repository.create(job)

    # Verify cleanup
    await repository.cleanup_test_data()
    all_jobs = await repository.get_company_jobs("company0", include_archived=True)
    assert len(all_jobs) == 0


@pytest.mark.asyncio
async def test_vector_search(repository):
    """Test vector search functionality for jobs"""
    logger.info("Starting vector search test")

    # Create test jobs with diverse descriptions
    jobs = [
        JobAd(
            company_id="company123",
            title="AI Engineer",
            description="Developing machine learning models and AI solutions using PyTorch and TensorFlow",
            requirements=["Python", "PyTorch", "TensorFlow"],
        ),
        JobAd(
            company_id="company456",
            title="Backend Developer",
            description="Building scalable backend services using Python and FastAPI",
            requirements=["Python", "FastAPI", "MongoDB"],
        ),
    ]

    for job in jobs:
        await repository.create(job)

    # Test semantic search
    results = await repository.search_similar(
        description="Looking for AI and machine learning positions", limit=2
    )
    assert len(results) > 0
    assert results[0].title == "AI Engineer"  # Most relevant should be first

    # Test search by requirements
    results = await repository.search_similar(
        description="Need experience with FastAPI and MongoDB", limit=2
    )
    assert len(results) > 0
    assert results[0].title == "Backend Developer"
