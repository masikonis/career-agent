from datetime import datetime
from typing import List, Optional

from bson import ObjectId

from src.utils.logger import get_logger

from .base import BaseRepository
from .database import MongoDB, RepositoryError
from .models import JobAd

logger = get_logger(__name__)


class JobRepository(BaseRepository[JobAd]):
    def __init__(self, db: MongoDB):
        super().__init__(db, "jobs", "Job")

    # === Core CRUD Operations ===
    async def create(self, job: JobAd) -> str:
        """Create a new job with embeddings"""
        try:
            # Generate embeddings for description and requirements
            job.description_embedding = await self._generate_embeddings(job.description)
            job_dict = self._to_document(job)
            result = await self.collection.insert_one(job_dict)
            logger.info(f"Created {self._entity_name} with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create {self._entity_name}: {str(e)}")
            raise RepositoryError(f"{self._entity_name} creation failed: {str(e)}")

    async def update_evaluation(
        self,
        job_id: str,
        match_score: float,
        skills_match: List[str],
        notes: Optional[str] = None,
    ) -> bool:
        """Update job evaluation scores and notes"""
        if not 0 <= match_score <= 1:
            logger.error(f"Invalid match score: {match_score}")
            raise ValueError("Match score must be between 0 and 1")

        update_dict = {
            "match_score": match_score,
            "skills_match": skills_match,
            "evaluation_notes": notes,
            "evaluated_at": datetime.now(),
        }
        return await self.update(job_id, update_dict)

    async def archive_job(self, job_id: str) -> bool:
        """Archive a job by marking it as inactive"""
        update_dict = {
            "active": False,
            "archived_at": datetime.now(),
        }
        return await self.update(job_id, update_dict)

    # === Query Operations ===
    async def get_company_jobs(
        self, company_id: str, include_archived: bool = False
    ) -> List[JobAd]:
        """Get all jobs for a company"""
        query = {"company_id": company_id}
        if not include_archived:
            query["active"] = True

        results, _ = await self.get_paginated(
            query=query, page=1, page_size=0  # No limit
        )
        return results

    async def get_best_matches(
        self, min_score: float = 0.7, limit: int = 10
    ) -> List[JobAd]:
        """Get best matching active jobs above minimum score"""
        query = {"active": True, "match_score": {"$gte": min_score}}
        results, _ = await self.get_paginated(
            query=query, page=1, page_size=limit, sort_by=[("match_score", -1)]
        )
        return results

    # === Search Operations ===
    async def search_similar(self, description: str, limit: int = 10) -> List[JobAd]:
        """Search similar jobs using vector similarity"""
        return await self._vector_search(
            text=description,
            embedding_field="description_embedding",
            limit=limit,
            additional_fields=["requirements_embedding"],
        )

    # === Utility Methods ===
    def _from_document(self, doc: dict) -> JobAd:
        """Convert MongoDB document to JobAd"""
        return JobAd(**doc)
