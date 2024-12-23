from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId

from src.utils.logger import get_logger

from .database import EntityNotFoundError, MongoDB, StorageError
from .models import Company, CompanyFilters

logger = get_logger(__name__)


class CompanyRepository:
    @classmethod
    async def create_repository(cls, is_test: bool = False) -> "CompanyRepository":
        db = await MongoDB.get_instance(is_test)
        return cls(db)

    def __init__(self, db: MongoDB):
        self.db = db
        self.collection = self.db.db.companies

    async def create(self, company: Company) -> str:
        """Create a new company"""
        try:
            company_dict = self._to_document(company)
            result = await self.collection.insert_one(company_dict)
            logger.info(f"Created company with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create company: {str(e)}")
            raise StorageError(f"Company creation failed: {str(e)}")

    async def get(self, company_id: str) -> Company:
        """Get company by ID"""
        try:
            logger.info(f"Attempting to get company with ID: {company_id}")
            object_id = ObjectId(company_id)
        except InvalidId:
            logger.error(f"Invalid company ID format: {company_id}")
            raise StorageError(f"Invalid company ID format: {company_id}")

        try:
            doc = await self.collection.find_one({"_id": object_id})
            if not doc:
                logger.warning(f"Company not found with ID: {company_id}")
                raise EntityNotFoundError("Company", company_id)

            doc["_id"] = str(doc["_id"])
            logger.info(f"Successfully retrieved company: {doc['name']}")
            return Company(**doc)
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to read company {company_id}: {str(e)}")
            raise StorageError(f"Company read failed: {str(e)}")

    async def update(self, company_id: str, company: Company) -> bool:
        """Update company"""
        try:
            company_dict = self._to_document(company)
            company_dict["updated_at"] = datetime.now()
            result = await self.collection.update_one(
                {"_id": ObjectId(company_id)}, {"$set": company_dict}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update company {company_id}: {str(e)}")
            raise StorageError(f"Company update failed: {str(e)}")

    async def delete(self, company_id: str) -> bool:
        """Delete company"""
        try:
            logger.info(f"Attempting to delete company with ID: {company_id}")
            result = await self.collection.delete_one({"_id": ObjectId(company_id)})
            success = result.deleted_count > 0
            if success:
                logger.info(f"Successfully deleted company {company_id}")
            else:
                logger.warning(f"No company found to delete with ID {company_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete company {company_id}: {str(e)}")
            raise StorageError(f"Company deletion failed: {str(e)}")

    async def get_all(self) -> List[Company]:
        """Get all companies"""
        try:
            cursor = self.collection.find({})
            docs = await cursor.to_list(length=None)
            for doc in docs:
                doc["_id"] = str(doc["_id"])
            return [Company(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Failed to get all companies: {str(e)}")
            raise StorageError(f"Failed to get all companies: {str(e)}")

    async def search(
        self,
        query: Optional[str] = None,
        filters: Optional[CompanyFilters] = None,
        limit: int = 10,
    ) -> List[Company]:
        try:
            filter_query = {}

            # Add text search if query provided
            if query:
                filter_query["$text"] = {"$search": query}

            # Add filters if provided
            if filters:
                if filters.industries:
                    filter_query["industry"] = {
                        "$in": [i.value for i in filters.industries]
                    }
                if filters.stages:
                    filter_query["stage"] = {"$in": [s.value for s in filters.stages]}
                if filters.min_match_score:
                    filter_query["company_fit_score"] = {
                        "$gte": filters.min_match_score
                    }
                if filters.date_from or filters.date_to:
                    filter_query["created_at"] = {}
                    if filters.date_from:
                        filter_query["created_at"]["$gte"] = filters.date_from
                    if filters.date_to:
                        filter_query["created_at"]["$lte"] = filters.date_to

            cursor = self.collection.find(filter_query)
            if query:  # Sort by text score only if text search is used
                cursor = cursor.sort([("score", {"$meta": "textScore"})])

            cursor = cursor.limit(limit)
            docs = await cursor.to_list(length=None)

            # Convert ObjectId to string for each document
            for doc in docs:
                doc["_id"] = str(doc["_id"])

            return [Company(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise StorageError(f"Search failed: {str(e)}")

    def _to_document(self, company: Company) -> dict:
        """Convert Company object to MongoDB document"""
        return company.model_dump(exclude={"id"}, by_alias=True, exclude_none=True)

    async def cleanup_test_data(self) -> None:
        """Clean up test data - only used in test environment"""
        if not isinstance(self.db, MongoDB) or not self.db.db.name.endswith("_test"):
            logger.warning("Attempted to cleanup non-test database! Aborting.")
            return

        try:
            await self.collection.delete_many({})
            logger.info("Successfully cleaned up test documents")
        except Exception as e:
            logger.error(f"Failed to cleanup test data: {str(e)}")
