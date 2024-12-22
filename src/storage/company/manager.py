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

    def __init__(self, storage: CompanyStorage):
        self.company_storage = storage
        logger = get_logger(__name__)

    async def search_companies(
        self, query: str, filters: Optional[CompanyFilters] = None, limit: int = 10
    ) -> List[Company]:
        """Search companies (placeholder until MongoDB vector search is implemented)"""
        # TODO: Implement MongoDB vector search
        logger.info("Vector search not yet implemented, returning all companies")
        # Temporary: Return all companies
        return await self.company_storage.get_all()

    async def find_similar_companies(
        self, company_id: EntityID, limit: int = 10
    ) -> List[Company]:
        """Find similar companies (placeholder until MongoDB vector search is implemented)"""
        # TODO: Implement MongoDB vector search for similarity
        logger.info("Similar company search not yet implemented")
        return []

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
