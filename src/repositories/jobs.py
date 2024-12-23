from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId

from src.utils.logger import get_logger

from .database import EntityNotFoundError, MongoDB, StorageError
from .models import JobAd

logger = get_logger(__name__)


class JobRepository:
    @classmethod
    async def create_repository(cls, is_test: bool = False) -> "JobRepository":
        db = await MongoDB.get_instance(is_test)
        return cls(db)

    def __init__(self, db: MongoDB):
        self.db = db
        self.collection = self.db.db.jobs

    async def create(self, job: JobAd) -> str:
        """Create a new job ad"""
        try:
            job_dict = self._to_document(job)
            result = await self.collection.insert_one(job_dict)
            logger.info(f"Created job ad with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create job ad: {str(e)}")
            raise StorageError(f"Job ad creation failed: {str(e)}")

    async def get(self, job_id: str) -> JobAd:
        """Get job by ID"""
        try:
            logger.info(f"Attempting to get job with ID: {job_id}")
            object_id = ObjectId(job_id)
        except InvalidId:
            logger.error(f"Invalid job ID format: {job_id}")
            raise StorageError(f"Invalid job ID format: {job_id}")

        try:
            doc = await self.collection.find_one({"_id": object_id})
            if not doc:
                logger.warning(f"Job not found with ID: {job_id}")
                raise EntityNotFoundError("Job", job_id)

            doc["_id"] = str(doc["_id"])
            logger.info(f"Successfully retrieved job: {doc['title']}")
            return JobAd(**doc)
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to read job {job_id}: {str(e)}")
            raise StorageError(f"Job read failed: {str(e)}")

    async def get_company_jobs(
        self, company_id: str, include_archived: bool = False
    ) -> List[JobAd]:
        """Get all jobs for a company"""
        try:
            query = {"company_id": company_id}
            if not include_archived:
                query["active"] = True

            cursor = self.collection.find(query)
            docs = await cursor.to_list(length=None)

            # Convert ObjectId to string
            for doc in docs:
                doc["_id"] = str(doc["_id"])

            logger.info(f"Found {len(docs)} jobs for company {company_id}")
            return [JobAd(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Failed to get company jobs: {str(e)}")
            raise StorageError(f"Failed to get company jobs: {str(e)}")

    async def update_evaluation(
        self,
        job_id: str,
        match_score: float,
        skills_match: List[str],
        notes: Optional[str] = None,
    ) -> bool:
        """Update job evaluation"""
        try:
            # Add validation
            if not 0 <= match_score <= 1:
                logger.error(
                    f"Invalid match score {match_score}. Must be between 0 and 1"
                )
                raise ValueError("Match score must be between 0 and 1")

            update_dict = {
                "match_score": match_score,
                "skills_match": skills_match,
                "evaluation_notes": notes,
                "evaluated_at": datetime.now(),
            }

            result = await self.collection.update_one(
                {"_id": ObjectId(job_id)}, {"$set": update_dict}
            )
            return result.modified_count > 0
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update job evaluation {job_id}: {str(e)}")
            raise StorageError(f"Job evaluation update failed: {str(e)}")

    async def archive_job(self, job_id: str) -> bool:
        """Archive a job"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(job_id)},
                {
                    "$set": {
                        "active": False,
                        "archived_at": datetime.now(),
                        "updated_at": datetime.now(),
                    }
                },
            )
            success = result.modified_count > 0
            if success:
                logger.info(f"Successfully archived job {job_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to archive job {job_id}: {str(e)}")
            raise StorageError(f"Job archive failed: {str(e)}")

    async def get_best_matches(
        self, min_score: float = 0.7, limit: int = 10
    ) -> List[JobAd]:
        """Get best matching active jobs"""
        try:
            cursor = (
                self.collection.find(
                    {"active": True, "match_score": {"$gte": min_score}}
                )
                .sort("match_score", -1)
                .limit(limit)
            )

            docs = await cursor.to_list(length=None)
            for doc in docs:
                doc["_id"] = str(doc["_id"])

            jobs = [JobAd(**doc) for doc in docs]
            logger.info(f"Found {len(jobs)} matching jobs with score >= {min_score}")
            return jobs
        except Exception as e:
            logger.error(f"Failed to get best matches: {str(e)}")
            raise StorageError("Failed to get best matches")

    def _to_document(self, job: JobAd) -> dict:
        """Convert JobAd object to MongoDB document"""
        return job.model_dump(exclude={"id"}, by_alias=True, exclude_none=True)

    async def cleanup_test_data(self) -> None:
        """Clean up test data - only used in test environment"""
        # Check if we're using a test database
        if "test" not in self.db.db.name.lower():
            logger.warning("Attempted to cleanup non-test database! Aborting.")
            return

        try:
            await self.collection.delete_many({})
            logger.info("Successfully cleaned up test job documents")
        except Exception as e:
            logger.error(f"Failed to cleanup test data: {str(e)}")
