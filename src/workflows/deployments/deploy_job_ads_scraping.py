from src.workflows.job_ads_scraping import job_ads_scraping_flow

job_ads_scraping_flow.from_source(
    source="https://github.com/masikonis/career-crew.git",
    entrypoint="src/workflows/job_ads_scraping.py:job_ads_scraping_flow",
).deploy(
    name="job-ads-scraping",
    work_pool_name="career-crew-pool",
)
