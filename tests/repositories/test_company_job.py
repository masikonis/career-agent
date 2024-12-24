from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from pydantic import ValidationError

from src.repositories.companies import CompanyRepository
from src.repositories.database import EntityNotFoundError, MongoDB, RepositoryError
from src.repositories.jobs import JobRepository
from src.repositories.models import (
    Company,
    CompanyFilters,
    CompanyIndustry,
    CompanyStage,
    JobAd,
)
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


@pytest.mark.asyncio
async def test_advanced_company_job_scenarios(repositories):
    """Test advanced scenarios for company and job interactions"""
    company_repo, job_repo = repositories
    logger.info("Starting advanced company-job scenarios test")

    # 1. Create multiple companies in different stages/industries
    companies = [
        Company(
            name="AI Startup",
            description="Early-stage AI research and development",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.SEED,
            website="https://ai-startup.com",
            company_fit_score=0.92,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Company(
            name="Data Analytics Corp",
            description="Enterprise data analytics solutions",
            industry=CompanyIndustry.SAAS,
            stage=CompanyStage.SERIES_A,
            website="https://data-analytics.com",
            company_fit_score=0.78,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    company_ids = []
    for company in companies:
        company_id = await company_repo.create(company)
        company_ids.append(company_id)
        logger.info(f"Created company: {company_id}")

    # 2. Add multiple jobs with varying characteristics
    jobs_data = [
        # High-match jobs for AI Startup
        (
            company_ids[0],
            [
                JobAd(
                    company_id=company_ids[0],
                    title="ML Research Engineer",
                    description="Deep learning research and implementation",
                    requirements=["PyTorch", "Research Experience", "PhD preferred"],
                    salary_range=(130000, 180000),
                    active=True,
                ),
                JobAd(
                    company_id=company_ids[0],
                    title="AI Product Manager",
                    description="Lead AI product development",
                    requirements=["Product Management", "AI Experience", "Agile"],
                    salary_range=(140000, 190000),
                    active=True,
                ),
            ],
        ),
        # Mixed-match jobs for Data Analytics Corp
        (
            company_ids[1],
            [
                JobAd(
                    company_id=company_ids[1],
                    title="Data Engineer",
                    description="Build data pipelines and analytics infrastructure",
                    requirements=["Python", "SQL", "Spark", "Airflow"],
                    salary_range=(120000, 160000),
                    active=True,
                ),
                JobAd(
                    company_id=company_ids[1],
                    title="Frontend Developer",
                    description="Build data visualization interfaces",
                    requirements=["React", "D3.js", "TypeScript"],
                    salary_range=(100000, 140000),
                    active=True,
                ),
            ],
        ),
    ]

    all_job_ids = []
    for company_id, jobs in jobs_data:
        for job in jobs:
            job_id = await job_repo.create(job)
            all_job_ids.append(job_id)
            logger.info(f"Created job: {job_id}")

    # 3. Test complex search scenarios
    # 3.1 Find AI companies with high match scores
    ai_companies = await company_repo.search(
        query="AI",
        filters=CompanyFilters(industries=[CompanyIndustry.SAAS], min_match_score=0.9),
    )
    assert len(ai_companies) == 1
    assert ai_companies[0].name == "AI Startup"

    # 3.2 Test similar company search
    similar_companies = await company_repo.search_similar(
        description="AI and machine learning research company", min_score=0.7
    )
    assert len(similar_companies) > 0
    assert "AI" in similar_companies[0].name

    # 4. Test job evaluation scenarios
    # 4.1 Evaluate jobs with different match levels
    evaluations = [
        (all_job_ids[0], 0.95, ["PyTorch", "Research"], "Perfect fit for ML research"),
        (all_job_ids[1], 0.82, ["Product Management"], "Good product role match"),
        (all_job_ids[2], 0.75, ["Python", "SQL"], "Partial skills match"),
        (all_job_ids[3], 0.45, ["React"], "Limited frontend experience"),
    ]

    for job_id, score, skills, notes in evaluations:
        await job_repo.update_evaluation(job_id, score, skills, notes)

    # 4.2 Test finding best matches across all companies
    best_matches = await job_repo.get_best_matches(min_score=0.8)
    assert len(best_matches) == 2
    assert all(job.match_score >= 0.8 for job in best_matches)

    # 5. Test company stage transition effects
    # 5.1 Update company stage and verify jobs
    company = companies[0]
    company.stage = CompanyStage.SERIES_A
    company.updated_at = datetime.now()
    await company_repo.update(company_ids[0], company)

    # 5.2 Archive some jobs after company update
    await job_repo.archive_job(all_job_ids[1])  # Archive AI Product Manager role

    # 5.3 Verify active vs archived jobs for the company
    active_jobs = await job_repo.get_company_jobs(
        company_ids[0], include_archived=False
    )
    all_jobs = await job_repo.get_company_jobs(company_ids[0], include_archived=True)
    assert len(active_jobs) == 1
    assert len(all_jobs) == 2

    # 6. Test job similarity search
    similar_jobs = await job_repo.search_similar(
        description="Machine learning and AI development position"
    )
    assert len(similar_jobs) > 0
    assert any("ML" in job.title or "AI" in job.title for job in similar_jobs)

    logger.info("Completed advanced company-job scenarios test")


@pytest.mark.asyncio
async def test_error_and_bulk_scenarios(repositories):
    """Test error handling and bulk operations for companies and jobs"""
    company_repo, job_repo = repositories
    logger.info("Starting error handling and bulk operations test")

    # 1. Setup test company
    company = Company(
        name="Tech Solutions Inc",
        description="Enterprise software solutions",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
        website="https://techsolutions.com",
        company_fit_score=0.80,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    company_id = await company_repo.create(company)

    # 2. Test error handling scenarios
    # 2.1 Invalid job evaluation score
    job = JobAd(
        company_id=company_id,
        title="Software Engineer",
        description="Backend development",
        requirements=["Python", "FastAPI"],
        salary_range=(100000, 150000),
        active=True,
    )
    original_job_id = await job_repo.create(job)

    with pytest.raises(ValueError):
        await job_repo.update_evaluation(
            original_job_id,
            match_score=1.5,  # Invalid score > 1
            skills_match=["Python"],
            notes="This should fail",
        )

    # 2.2 Non-existent company/job
    fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId but doesn't exist
    with pytest.raises(EntityNotFoundError):
        # First verify the job doesn't exist
        await job_repo.get(fake_id)  # This should raise EntityNotFoundError

    # 2.3 Invalid company-job relationship
    invalid_job = JobAd(
        company_id=fake_id,  # Non-existent company
        title="Invalid Job",
        description="This job has an invalid company reference",
        requirements=["Python"],
        active=True,
    )
    # This should create the job but might cause issues in related operations
    invalid_job_id = await job_repo.create(invalid_job)

    # Verify we can still get this job despite invalid company reference
    retrieved_job = await job_repo.get(invalid_job_id)
    assert retrieved_job.company_id == fake_id

    # 3. Bulk operations scenarios
    # 3.1 Create multiple jobs for bulk testing
    bulk_jobs = [
        JobAd(
            company_id=company_id,
            title=f"Bulk Test Job {i}",
            description=f"Test job description {i}",
            requirements=["Python", "FastAPI"],
            salary_range=(100000, 150000),
            active=True,
        )
        for i in range(5)
    ]

    bulk_job_ids = []
    for job in bulk_jobs:
        job_id = await job_repo.create(job)
        bulk_job_ids.append(job_id)

    # 3.2 Bulk job evaluation
    evaluation_data = [
        (0.85, ["Python", "FastAPI"], "Good match"),
        (0.75, ["Python"], "Partial match"),
        (0.95, ["Python", "FastAPI", "MongoDB"], "Excellent match"),
        (0.65, ["Python"], "Basic match"),
        (0.80, ["Python", "FastAPI"], "Strong match"),
    ]

    # First evaluate the original Software Engineer job
    logger.info(f"Evaluating original job (ID: {original_job_id})")
    success = await job_repo.update_evaluation(
        original_job_id,
        match_score=0.70,
        skills_match=["Python", "FastAPI"],
        notes="Original job evaluation",
    )
    assert success is True, "Failed to evaluate original job"

    # Verify the original job evaluation worked
    original_job = await job_repo.get(original_job_id)
    logger.info(
        f"Original job after evaluation - match_score: {original_job.match_score}"
    )
    assert original_job.match_score == 0.70, "Original job evaluation didn't persist"

    # Then evaluate all bulk jobs
    for bulk_job_id, (score, skills, notes) in zip(bulk_job_ids, evaluation_data):
        success = await job_repo.update_evaluation(bulk_job_id, score, skills, notes)
        assert success is True, f"Failed to evaluate bulk job {bulk_job_id}"

    # 3.3 Verify bulk evaluations
    evaluated_jobs = await job_repo.get_company_jobs(company_id)

    # Debug: Print each job's match score
    for job in evaluated_jobs:
        logger.info(f"Job '{job.title}' has match_score: {job.match_score}")

    # First verify the count
    assert len(evaluated_jobs) == 6  # 5 bulk jobs + 1 original

    # Then verify each job has a match score
    jobs_without_scores = [
        job.title for job in evaluated_jobs if job.match_score is None
    ]
    assert (
        not jobs_without_scores
    ), f"These jobs have no match score: {jobs_without_scores}"

    # 3.4 Test company stage change affecting all jobs
    company.stage = CompanyStage.SERIES_A
    company.updated_at = datetime.now()
    await company_repo.update(company_id, company)

    # 3.5 Bulk archive jobs based on criteria
    low_scoring_jobs = [
        job for job in evaluated_jobs if job.match_score and job.match_score < 0.8
    ]
    for job in low_scoring_jobs:
        await job_repo.archive_job(str(job.id))

    # 3.6 Verify bulk archiving
    active_jobs = await job_repo.get_company_jobs(company_id, include_archived=False)
    archived_jobs = await job_repo.get_company_jobs(company_id, include_archived=True)
    assert len(active_jobs) < len(archived_jobs)
    assert all(job.match_score >= 0.8 for job in active_jobs)

    # 4. Test data consistency
    # 4.1 Verify all jobs have proper timestamps
    all_jobs = await job_repo.get_company_jobs(company_id, include_archived=True)
    for job in all_jobs:
        assert job.created_at is not None
        if not job.active:
            assert job.archived_at is not None
        if job.match_score is not None:
            assert job.evaluated_at is not None

    # 4.2 Verify company relationship integrity
    company_jobs = await job_repo.get_company_jobs(company_id, include_archived=True)
    assert all(job.company_id == company_id for job in company_jobs)

    logger.info("Completed error handling and bulk operations test")


@pytest.mark.asyncio
async def test_company_lifecycle_scenarios(repositories):
    """Test company lifecycle and its impact on jobs"""
    company_repo, job_repo = repositories
    logger.info("Starting company lifecycle test")

    # 1. Setup: Create company with multiple jobs
    company = Company(
        name="Growth Startup",
        description="Fast-growing tech startup",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
        website="https://growth-startup.com",
        company_fit_score=0.88,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    company_id = await company_repo.create(company)

    # Create jobs at different stages
    jobs = [
        JobAd(
            company_id=company_id,
            title="Senior Developer",
            description="Lead development role",
            requirements=["Python", "Leadership"],
            salary_range=(130000, 180000),
            active=True,
        ),
        JobAd(
            company_id=company_id,
            title="Product Designer",
            description="Design product experience",
            requirements=["Figma", "User Research"],
            salary_range=(110000, 150000),
            active=True,
        ),
    ]

    job_ids = []
    for job in jobs:
        job_id = await job_repo.create(job)
        job_ids.append(job_id)

    # 2. Test company stage transitions
    # 2.1 Seed to Series A transition
    company.stage = CompanyStage.SERIES_A
    company.updated_at = datetime.now()
    await company_repo.update(company_id, company)

    # Verify company update
    updated_company = await company_repo.get(company_id)
    assert updated_company.stage == CompanyStage.SERIES_A

    # 2.2 Update job requirements after funding
    new_requirements = ["Python", "Leadership", "Scale Experience"]
    await job_repo.update(job_ids[0], {"requirements": new_requirements})

    updated_job = await job_repo.get(job_ids[0])
    assert "Scale Experience" in updated_job.requirements

    # 3. Test company search with multiple criteria
    # 3.1 Search by industry and stage
    series_a_companies = await company_repo.search(
        filters=CompanyFilters(
            industries=[CompanyIndustry.SAAS],
            stages=[CompanyStage.SERIES_A],
            min_match_score=0.8,
        )
    )
    assert len(series_a_companies) == 1
    assert series_a_companies[0].name == "Growth Startup"

    # 3.2 Search by date range
    recent_companies = await company_repo.search(
        filters=CompanyFilters(
            date_from=datetime.now() - timedelta(hours=1),
            date_to=datetime.now() + timedelta(hours=1),
        )
    )
    assert len(recent_companies) > 0

    # 4. Test job archiving scenarios
    # 4.1 Archive job with replacement
    await job_repo.archive_job(job_ids[0])  # Archive Senior Developer role

    # Create replacement job
    new_job = JobAd(
        company_id=company_id,
        title="Engineering Manager",  # Upgraded role
        description="Lead engineering team and scale operations",
        requirements=["Python", "Leadership", "Scale Experience"],
        salary_range=(150000, 200000),
        active=True,
    )
    new_job_id = await job_repo.create(new_job)

    # 4.2 Verify active vs archived jobs
    active_jobs = await job_repo.get_company_jobs(company_id, include_archived=False)
    assert len(active_jobs) == 2  # Product Designer + Engineering Manager

    all_jobs = await job_repo.get_company_jobs(company_id, include_archived=True)
    assert len(all_jobs) == 3  # Including archived Senior Developer

    # 4.3 Verify job history is maintained
    archived_jobs = [job for job in all_jobs if not job.active]
    assert len(archived_jobs) == 1
    assert archived_jobs[0].title == "Senior Developer"
    assert archived_jobs[0].archived_at is not None

    # 5. Test similar job search with context
    similar_jobs = await job_repo.search_similar(
        description="Engineering leadership and team scaling"
    )
    assert any("Engineering Manager" in job.title for job in similar_jobs)

    logger.info("Completed company lifecycle test")


@pytest.mark.asyncio
async def test_edge_cases_and_validations(repositories):
    """Test edge cases and validation scenarios"""
    company_repo, job_repo = repositories
    logger.info("Starting edge cases and validation test")

    # 1. Test empty description handling
    company = Company(
        name="Empty Desc Co",
        description="",  # Empty description
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
        website="https://empty-desc.com",
        company_fit_score=0.75,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    company_id = await company_repo.create(company)
    assert company_id, "Should handle empty description"

    # 2. Test combined search criteria
    companies = await company_repo.search(
        query="Empty",  # Text search
        filters=CompanyFilters(  # Combined with filters
            industries=[CompanyIndustry.SAAS],
            stages=[CompanyStage.SEED],
            min_match_score=0.7,
        ),
        limit=5,
    )
    assert len(companies) == 1
    assert companies[0].name == "Empty Desc Co"

    # 3. Test empty search results
    no_results = await company_repo.search(query="NonexistentCompany123", limit=10)
    assert len(no_results) == 0

    # 4. Test vector search with min_score
    similar_companies = await company_repo.search_similar(
        description="Software company", min_score=0.99  # Very high threshold
    )
    assert (
        len(similar_companies) == 0
    )  # Should find no matches with such high threshold

    # 5. Test job with invalid salary range
    with pytest.raises(ValidationError):
        job = JobAd(
            company_id=company_id,
            title="Invalid Salary Job",
            description="Test job",
            requirements=["Python"],
            salary_range=(200000, 100000),  # Max less than min
            active=True,
        )
        # Note: We don't even need to call create() since the validation fails at model creation

    # 6. Test job with valid salary range
    job = JobAd(
        company_id=company_id,
        title="Valid Salary Job",
        description="Test job",
        requirements=["Python"],
        salary_range=(100000, 200000),  # Valid range
        active=True,
    )
    job_id = await job_repo.create(job)
    assert job_id, "Should create job with valid salary range"

    # 7. Test duplicate company detection
    duplicate_company = Company(
        name="Empty Desc Co",  # Same name
        description="Different description",
        industry=CompanyIndustry.SAAS,
        stage=CompanyStage.SEED,
        website="https://empty-desc.com",  # Same website
        company_fit_score=0.75,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    with pytest.raises(RepositoryError):
        await company_repo.create(duplicate_company)

    # 8. Test invalid stage transition
    company.stage = CompanyStage.EARLY
    await company_repo.update(company_id, company)  # SEED -> EARLY (valid)

    company.stage = CompanyStage.SEED
    with pytest.raises(ValueError):
        await company_repo.update(company_id, company)  # EARLY -> SEED (invalid)

    # 9. Test job search with empty requirements
    job = JobAd(
        company_id=company_id,
        title="No Requirements Job",
        description="Test job",
        requirements=[],  # Empty requirements
        salary_range=(100000, 150000),
        active=True,
    )
    job_id = await job_repo.create(job)
    assert job_id, "Should handle empty requirements"

    similar_jobs = await job_repo.search_similar(
        description="Test job with no requirements"
    )
    assert any(j.id == job_id for j in similar_jobs)

    logger.info("Completed edge cases and validation test")
