from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from src.repositories.companies import CompanyRepository
from src.repositories.database import MongoDB
from src.repositories.jobs import JobRepository
from src.repositories.models import Company, CompanyIndustry, CompanyStage, JobAd
from src.utils.logger import get_logger

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def repositories():
    """Setup test repositories with clean database"""
    await MongoDB.reset_instance()
    db = await MongoDB.get_instance(is_test=True)

    company_repo = CompanyRepository(db)
    job_repo = JobRepository(db)

    yield company_repo, job_repo

    # Cleanup
    await company_repo.collection.delete_many({})
    await job_repo.collection.delete_many({})
    await MongoDB.reset_instance()


@pytest.mark.asyncio
async def test_company_job_workflow(repositories):
    """Test complete workflow of company discovery and job management"""
    company_repo, job_repo = repositories
    logger.info("Starting company-job workflow test")

    # 1. Create company (simulating company research agent results)
    company = Company(
        name="TechCorp AI",
        description="Leading AI solutions provider focusing on ML infrastructure",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
        website="https://techcorp-ai.com",
        company_fit_score=0.85,  # High company fit
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    company_id = await company_repo.create(company)
    logger.info(f"Created company: {company_id}")

    # 2. Add multiple jobs for the company
    jobs = [
        JobAd(
            company_id=company_id,
            title="Senior ML Engineer",
            description="Lead ML infrastructure development",
            requirements=["Python", "PyTorch", "Kubernetes"],
            salary_range=(150000, 200000),
            active=True,
        ),
        JobAd(
            company_id=company_id,
            title="DevOps Engineer",
            description="Managing cloud infrastructure",
            requirements=["AWS", "Terraform", "Docker"],
            salary_range=(130000, 170000),
            active=True,
        ),
    ]

    job_ids = []
    for job in jobs:
        job_id = await job_repo.create(job)
        job_ids.append(job_id)
        logger.info(f"Created job: {job_id}")

    # 3. Test job evaluations
    await job_repo.update_evaluation(
        job_ids[0],
        match_score=0.9,  # High match for ML role
        skills_match=["Python", "PyTorch"],
        notes="Strong match for ML skills",
    )

    await job_repo.update_evaluation(
        job_ids[1],
        match_score=0.6,  # Lower match for DevOps
        skills_match=["AWS"],
        notes="Partial match for cloud skills",
    )

    # 4. Verify company's jobs
    company_jobs = await job_repo.get_company_jobs(company_id)
    assert len(company_jobs) == 2
    assert any(job.match_score == 0.9 for job in company_jobs)
    assert any(job.match_score == 0.6 for job in company_jobs)

    # 5. Test company update scenario
    company.stage = CompanyStage.SERIES_A
    company.updated_at = datetime.now()
    success = await company_repo.update(company_id, company)
    assert success is True

    updated_company = await company_repo.get(company_id)
    assert updated_company.stage == CompanyStage.SERIES_A

    # 6. Test job archiving when company changes
    await job_repo.archive_job(job_ids[1])  # Archive DevOps position

    # Verify active vs archived jobs
    active_jobs = await job_repo.get_company_jobs(company_id, include_archived=False)
    assert len(active_jobs) == 1
    assert active_jobs[0].title == "Senior ML Engineer"

    all_jobs = await job_repo.get_company_jobs(company_id, include_archived=True)
    assert len(all_jobs) == 2

    # 7. Test searching for best matches
    best_matches = await job_repo.get_best_matches(min_score=0.8)
    assert len(best_matches) == 1
    assert best_matches[0].match_score >= 0.8
    assert best_matches[0].title == "Senior ML Engineer"

    # 8. Test company similarity search
    similar_companies = await company_repo.search_similar(
        description="AI infrastructure and machine learning solutions", min_score=0.7
    )
    assert len(similar_companies) > 0
    assert similar_companies[0].name == "TechCorp AI"

    logger.info("Completed company-job workflow test successfully")
