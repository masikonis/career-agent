from prefect import flow, get_run_context, task

from src.utils.logger import get_logger

logger = get_logger(__name__)


@task
async def log_workflow_start(workflow_name: str):
    """Log the start of a workflow"""
    try:
        context = get_run_context()
        logger.info(
            f"Starting workflow: {workflow_name}",
            extra={"flow_name": context.flow_name},
        )
    except Exception as e:
        logger.warning(f"Could not get flow context: {e}")


@task
async def log_workflow_end(workflow_name: str):
    """Log the end of a workflow"""
    try:
        context = get_run_context()
        logger.info(
            f"Completed workflow: {workflow_name}",
            extra={"flow_name": context.flow_name},
        )
    except Exception as e:
        logger.warning(f"Could not get flow context: {e}")
