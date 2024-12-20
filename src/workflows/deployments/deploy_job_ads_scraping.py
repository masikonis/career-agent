from datetime import timedelta

from prefect import flow

from src.workflows.job_ads_scraping import job_ads_scraping_flow

if __name__ == "__main__":
    deployment = job_ads_scraping_flow.to_deployment(
        name="job-ads-scraping",
        work_pool_name="career-crew-pool",
        interval=timedelta(hours=24),
        storage={
            "type": "github",
            "repository": "masikonis/career-crew",
            "reference": "main",
        },
    )
    deployment.apply()
