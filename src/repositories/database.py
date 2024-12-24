import asyncio
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryError(Exception):
    """Base exception for repository operations"""

    pass


class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found"""

    def __init__(self, entity_type: str, entity_id: str):
        self.message = f"{entity_type} with id {entity_id} not found"
        super().__init__(self.message)


class MongoDB:
    _instance: Optional["MongoDB"] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, is_test: bool = False) -> "MongoDB":
        async with cls._lock:
            if not cls._instance:
                cls._instance = cls(is_test)
                await cls._instance._create_indexes()
            return cls._instance

    @classmethod
    async def reset_instance(cls):
        """Reset singleton instance (useful for testing)"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

    def __init__(self, is_test: bool = False):
        self.client = AsyncIOMotorClient(config["MONGODB_URI"])
        db_name = (
            f"{config['MONGODB_DB_NAME']}-test"
            if is_test
            else config["MONGODB_DB_NAME"]
        )
        self.db = self.client[db_name]

    async def _create_indexes(self):
        """Create all required indexes"""
        try:
            # Drop existing indexes first in test environment
            if "test" in self.db.name.lower():
                await self.db.companies.drop_indexes()
                await self.db.jobs.drop_indexes()
                logger.info("Dropped existing indexes in test database")

            # Regular indexes for companies
            await self.db.companies.create_index("name")
            await self.db.companies.create_index("industry")
            await self.db.companies.create_index("stage")
            await self.db.companies.create_index("company_fit_score")

            # Regular indexes for jobs
            await self.db.jobs.create_index("company_id")
            await self.db.jobs.create_index("active")
            await self.db.jobs.create_index("match_score")

            # Text search indexes
            await self.db.companies.create_index(
                [("name", "text"), ("description", "text")],
                weights={"name": 2, "description": 1},
            )

            await self.db.jobs.create_index(
                [("title", "text"), ("description", "text"), ("requirements", "text")],
                weights={"title": 3, "description": 2, "requirements": 1},
            )

            logger.info("Successfully created all indexes")
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise RepositoryError(f"Failed to create database indexes: {str(e)}")

    async def close(self):
        self.client.close()
        logger.info("Closed MongoDB connection")
