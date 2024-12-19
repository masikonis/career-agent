from datetime import datetime
from typing import List, Optional

from src.utils.logger import get_logger

from ..base.exceptions import StorageOperationError, StorageSyncError
from ..base.types import EntityID, Metadata
from ..managers.base import BaseStorageManager
from .interfaces import CompanySearchIndex, CompanyStorage
from .types import (
    Company,
    CompanyEvaluation,
    CompanyFilters,
    CompanyIndustry,
    CompanyStage,
)

logger = get_logger(__name__)


class CompanyStorageManager(BaseStorageManager[Company]):
    """
    Manages company storage and search operations.
    Coordinates between primary storage and search index.
    """

    def __init__(self, storage: CompanyStorage, search_index: CompanySearchIndex):
        super().__init__(storage, search_index)
        self.company_storage = storage  # Type-specific reference
        self.company_search = search_index  # Type-specific reference

    def _create_metadata(self, company: Company) -> Metadata:
        """Create metadata for company indexing"""
        # Convert string values back to enums if needed
        industry = (
            company.industry
            if isinstance(company.industry, CompanyIndustry)
            else CompanyIndustry(company.industry)
        )
        stage = (
            company.stage
            if isinstance(company.stage, CompanyStage)
            else CompanyStage(company.stage)
        )

        return {
            "name": company.name,
            "description": company.description,
            "industry": industry.value,
            "stage": stage.value,
            "created_at": str(company.created_at),
            "updated_at": str(company.updated_at),
            "entity_type": "company",
        }

    async def find_similar_companies(
        self, company_id: EntityID, limit: int = 10
    ) -> List[Company]:
        """Find companies similar to the given company"""
        try:
            return await self.company_search.search_similar(company_id, limit)
        except Exception as e:
            logger.error(f"Failed to find similar companies: {str(e)}")
            raise StorageOperationError("similar_search", str(e))

    async def search_companies(
        self, query: str, filters: Optional[CompanyFilters] = None, limit: int = 10
    ) -> List[Company]:
        """Search companies with optional filters"""
        try:
            # Get IDs from search index with filters
            entity_ids = await self.company_search.search(query)

            # Fetch full company data
            companies = []
            for entity_id in entity_ids:
                if company := await self.get(entity_id):
                    companies.append(company)

            return companies
        except Exception as e:
            logger.error(f"Failed to search companies: {str(e)}")
            raise StorageOperationError("company_search", str(e))

    async def add_evaluation(
        self, company_id: EntityID, evaluation: CompanyEvaluation
    ) -> bool:
        """Add an evaluation to a company and update search metadata"""
        try:
            # Add evaluation to storage
            success = await self.company_storage.add_evaluation(company_id, evaluation)
            if not success:
                raise StorageOperationError(
                    "add_evaluation", "Failed to add evaluation"
                )

            # Update company in search index with new metadata
            company = await self.get(company_id)
            if company:
                metadata = self._create_metadata(company)
                await self.search_index.index(company_id, company, metadata)

            return True
        except Exception as e:
            logger.error(f"Failed to add evaluation: {str(e)}")
            raise StorageOperationError("add_evaluation", str(e))

    async def get_evaluations(self, company_id: EntityID) -> List[CompanyEvaluation]:
        """Get all evaluations for a company"""
        try:
            return await self.company_storage.get_evaluations(company_id)
        except Exception as e:
            logger.error(f"Failed to get evaluations: {str(e)}")
            raise StorageOperationError("get_evaluations", str(e))

    async def create(self, company: Company) -> EntityID:
        """Create a company and index it for search"""
        try:
            # Create in primary storage first
            entity_id = await self.company_storage.create(company)

            # Create metadata for search indexing
            metadata = {
                "name": company.name,
                "description": company.description,
                "industry": company.industry.value,
                "stage": company.stage.value,
                "created_at": company.created_at.isoformat(),
                "updated_at": company.updated_at.isoformat(),
                "entity_type": "company",
            }

            # Index in search
            await self.company_search.index(entity_id, company, metadata)

            return entity_id

        except Exception as e:
            logger.error(f"Failed to create company: {str(e)}")
            raise StorageOperationError("company_create", str(e))

    async def delete(self, company_id: EntityID) -> bool:
        """Delete a company from both storage and search index"""
        try:
            # Delete from MongoDB
            success = await self.company_storage.delete(company_id)
            if not success:
                raise StorageOperationError(
                    "delete", f"Failed to delete company {company_id} from storage"
                )

            # Delete from search index
            success = await self.search_index.delete(company_id)
            if not success:
                logger.warning(
                    f"Failed to delete company {company_id} from search index"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to delete company {company_id}: {str(e)}")
            raise StorageOperationError("delete", str(e))
