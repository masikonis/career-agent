from datetime import datetime
from typing import List, Optional

from bson import ObjectId

from src.utils.logger import get_logger

from .base import BaseRepository
from .database import EntityNotFoundError, MongoDB, RepositoryError
from .models import Company, CompanyFilters, CompanyStage

logger = get_logger(__name__)


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: MongoDB):
        super().__init__(db, "companies", "Company")

    # === Core CRUD Operations ===
    async def create(self, company: Company) -> str:
        """Create a new company with embeddings"""
        try:
            # Generate embeddings for description only
            company.description_embedding = await self._generate_embeddings(
                company.description
            )
            company_dict = self._to_document(company)
            result = await self.collection.insert_one(company_dict)
            logger.info(f"Created {self._entity_name} with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create {self._entity_name}: {str(e)}")
            raise RepositoryError(f"{self._entity_name} creation failed: {str(e)}")

    async def update(self, company_id: str, company: Company) -> bool:
        """Update company with stage transition validation"""
        try:
            # First get the current company state
            try:
                current_company = await self.get(company_id)
            except EntityNotFoundError:
                logger.warning(f"Cannot update non-existent company: {company_id}")
                return False

            # Validate stage transition
            if current_company.stage != company.stage:
                if self._is_invalid_stage_transition(
                    current_company.stage, company.stage
                ):
                    logger.error(
                        f"Invalid stage transition from {current_company.stage} to {company.stage}"
                    )
                    raise ValueError(
                        f"Cannot transition company from {current_company.stage} to {company.stage}"
                    )

            company_dict = self._to_document(company)
            return await super().update(company_id, company_dict)
        except Exception as e:
            logger.error(f"Failed to update {self._entity_name}: {str(e)}")
            raise

    # === Search Operations ===
    async def search(
        self,
        query: Optional[str] = None,
        filters: Optional[CompanyFilters] = None,
        limit: int = 10,
    ) -> List[Company]:
        """Search companies by text and/or filters"""
        try:
            filter_query = self._build_filter_query(filters) if filters else {}

            if query:
                # Use MongoDB text search
                filter_query["$text"] = {"$search": query}
                results, _ = await self.get_paginated(
                    query=filter_query,
                    page=1,
                    page_size=limit,
                    sort_by=[("score", {"$meta": "textScore"})],
                )
                return results

            # Handle filter-only case
            results, _ = await self.get_paginated(
                query=filter_query, page=1, page_size=limit
            )
            return results
        except Exception as e:
            logger.error(f"Search failed in {self._entity_name}: {str(e)}")
            raise RepositoryError(f"Search failed: {str(e)}")

    async def search_similar(
        self, description: str, limit: int = 10, min_score: Optional[float] = None
    ) -> List[Company]:
        """Search similar companies using vector similarity"""
        return await self._vector_search(
            text=description,
            embedding_field="description_embedding",
            limit=limit,
            min_score=min_score,
            score_field="company_fit_score",
        )

    # === Utility Methods ===
    def _from_document(self, doc: dict) -> Company:
        """Convert MongoDB document to Company"""
        return Company(**doc)

    def _to_document(self, company: Company) -> dict:
        """Convert Company to MongoDB document"""
        return company.model_dump(exclude={"id"}, by_alias=True, exclude_none=True)

    def _build_filter_query(self, filters: CompanyFilters) -> dict:
        """Build MongoDB query from filters"""
        filter_query = {}
        if filters.industries:
            filter_query["industry"] = {"$in": [i.value for i in filters.industries]}
        if filters.stages:
            filter_query["stage"] = {"$in": [s.value for s in filters.stages]}
        if filters.min_match_score:
            filter_query["company_fit_score"] = {"$gte": filters.min_match_score}
        if filters.date_from or filters.date_to:
            filter_query["created_at"] = {}
            if filters.date_from:
                filter_query["created_at"]["$gte"] = filters.date_from
            if filters.date_to:
                filter_query["created_at"]["$lte"] = filters.date_to
        return filter_query

    def _is_invalid_stage_transition(
        self, current_stage: CompanyStage, new_stage: CompanyStage
    ) -> bool:
        """
        Validate company stage transitions.
        Companies can only progress forward in stages:
        IDEA -> PRE_SEED -> MVP -> SEED -> EARLY -> SERIES_A -> LATER
        """
        stage_order = {
            CompanyStage.IDEA: 0,
            CompanyStage.PRE_SEED: 1,
            CompanyStage.MVP: 2,
            CompanyStage.SEED: 3,
            CompanyStage.EARLY: 4,
            CompanyStage.SERIES_A: 5,
            CompanyStage.LATER: 6,
        }

        # Get numeric values for stages
        current_value = stage_order[current_stage]
        new_value = stage_order[new_stage]

        # Cannot go backwards in stages
        return new_value < current_value
