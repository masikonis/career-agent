from datetime import timedelta

from prefect import flow

from src.workflows.job_ads_scraping import job_ads_scraping_flow

if __name__ == "__main__":
    job_ads_scraping_flow.from_source(
        source="https://github.com/masikonis/career-crew.git",
        entrypoint="src/workflows/job_ads_scraping.py:job_ads_scraping_flow",
        reference="main",
    ).deploy(
        name="job-ads-scraping",
        work_pool_name="career-crew-pool",
        interval=timedelta(hours=4),
        build=False,
    )
