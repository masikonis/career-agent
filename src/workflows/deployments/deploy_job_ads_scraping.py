from datetime import timedelta

from prefect import flow
from prefect.filesystems import GitHub

from src.workflows.job_ads_scraping import job_ads_scraping_flow

if __name__ == "__main__":
    # First, create and save the GitHub block
    github_block = GitHub(
        name="career-crew-repo",
        repository="https://github.com/masikonis/career-crew.git",
        reference="main",
    )
    github_block.save()

    # Then use it in the deployment
    deployment = job_ads_scraping_flow.to_deployment(
        name="job-ads-scraping",
        work_pool_name="career-crew-pool",
        interval=timedelta(hours=4),
        storage=github_block,
    )
    deployment.apply()
