from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union

from bson import ObjectId
from bson.errors import InvalidId
from langchain_openai import OpenAIEmbeddings

from src.utils.logger import get_logger

from .database import EntityNotFoundError, MongoDB, RepositoryError

logger = get_logger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common operations"""

    def __init__(self, db: MongoDB, collection_name: str, entity_name: str):
        self.db = db
        self.collection = self.db.db[collection_name]
        self._entity_name = entity_name
        self.embeddings = OpenAIEmbeddings()

    # === Core CRUD Operations ===
    async def get(self, id: str) -> T:
        """Get entity by ID"""
        try:
            object_id = ObjectId(id)
        except InvalidId:
            logger.error(f"Invalid {self._entity_name} ID format: {id}")
            raise RepositoryError(f"Invalid {self._entity_name} ID format: {id}")

        try:
            doc = await self.collection.find_one({"_id": object_id})
            if not doc:
                logger.warning(f"{self._entity_name} not found with ID: {id}")
                raise EntityNotFoundError(self._entity_name, id)

            doc["_id"] = str(doc["_id"])
            return self._from_document(doc)
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to read {self._entity_name} {id}: {str(e)}")
            raise RepositoryError(f"{self._entity_name} read failed: {str(e)}")

    async def update(self, id: str, update_data: Union[dict, T]) -> bool:
        """Update entity with specific fields"""
        try:
            # Convert Pydantic model to dict if needed
            update_dict = (
                update_data.model_dump(exclude={"id"}, by_alias=True, exclude_none=True)
                if hasattr(update_data, "model_dump")
                else update_data
            )

            update_dict["updated_at"] = datetime.now()
            result = await self.collection.update_one(
                {"_id": ObjectId(id)}, {"$set": update_dict}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update {self._entity_name} {id}: {str(e)}")
            raise RepositoryError(f"{self._entity_name} update failed: {str(e)}")

    async def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        try:
            logger.info(f"Attempting to delete {self._entity_name} with ID: {id}")
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            success = result.deleted_count > 0
            if success:
                logger.info(f"Successfully deleted {self._entity_name} {id}")
            else:
                logger.warning(f"No {self._entity_name} found to delete with ID {id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete {self._entity_name} {id}: {str(e)}")
            raise RepositoryError(f"{self._entity_name} deletion failed: {str(e)}")

    # === Query Operations ===
    async def get_all(self) -> List[T]:
        """Get all entities without pagination"""
        results, _ = await self.get_paginated(query={}, page=1, page_size=0)  # No limit
        return results

    async def get_paginated(
        self,
        query: dict = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = None,
    ) -> Tuple[List[T], int]:
        """Get paginated results with total count"""
        try:
            skip = (page - 1) * page_size
            cursor = self.collection.find(query or {})

            if sort_by:
                cursor = cursor.sort(sort_by)

            total = await self.collection.count_documents(query or {})
            docs = await cursor.skip(skip).limit(page_size).to_list(None)
            docs = self._process_documents(docs)

            return [self._from_document(doc) for doc in docs], total
        except Exception as e:
            logger.error(f"Pagination failed: {str(e)}")
            raise RepositoryError(f"Pagination failed: {str(e)}")

    # === Search Operations ===
    async def search_text(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        sort_field: Optional[str] = None,
    ) -> List[T]:
        """Common text search implementation"""
        try:
            filter_query = {"$text": {"$search": query}}
            if filters:
                filter_query.update(filters)

            cursor = self.collection.find(filter_query)
            if sort_field:
                cursor = cursor.sort(sort_field)

            cursor = cursor.limit(limit)
            docs = await cursor.to_list(length=None)
            docs = self._process_documents(docs)

            return [self._from_document(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise RepositoryError(f"Search failed: {str(e)}")

    async def _vector_search(
        self,
        text: str,
        embedding_field: str,
        limit: int = 10,
        min_score: Optional[float] = None,
        score_field: Optional[str] = None,
        additional_fields: Optional[List[str]] = None,
    ) -> List[T]:
        """Perform vector similarity search (mocked for testing)"""
        try:
            # For testing, use simple text matching instead of vector search
            if "test" in self.db.db.name.lower():
                # Simple text search as a mock
                query = {"$text": {"$search": text}}
                if min_score is not None and score_field:
                    query[score_field] = {"$gte": min_score}

                cursor = self.collection.find(query).limit(limit)
                docs = await cursor.to_list(length=None)
                docs = self._process_documents(docs)
                return [self._from_document(doc) for doc in docs]

            # Real vector search implementation (for production)
            pipeline = [
                {
                    "$vectorSearch": {
                        "queryVector": await self._generate_embeddings(text),
                        "path": embedding_field,
                        "numCandidates": limit * 10,
                        "limit": limit,
                        "index": "vector_index",
                    }
                }
            ]

            if min_score is not None and score_field:
                pipeline.append({"$match": {score_field: {"$gte": min_score}}})

            results = []
            async for doc in self.collection.aggregate(pipeline):
                doc["_id"] = str(doc["_id"])
                results.append(self._from_document(doc))

            return results
        except Exception as e:
            logger.error(f"Vector search failed in {self._entity_name}: {str(e)}")
            raise RepositoryError(f"Vector search failed: {str(e)}")

    # === Utility Methods ===
    def _to_document(self, item: T) -> dict:
        """Convert object to MongoDB document"""
        return item.model_dump(exclude={"id"}, by_alias=True, exclude_none=True)

    def _from_document(self, doc: dict) -> T:
        """Convert MongoDB document to entity - must be implemented by subclasses"""
        raise NotImplementedError

    def _process_documents(self, docs: List[dict]) -> List[dict]:
        """Convert ObjectIds to strings in document list"""
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs

    async def _generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text using OpenAI"""
        return await self.embeddings.aembed_query(text)

    # === Test Helpers ===
    async def cleanup_test_data(self) -> None:
        """Clean up test data - only used in test environment"""
        if "test" not in self.db.db.name.lower():
            logger.warning(
                f"Attempted to cleanup non-test {self._entity_name} database! Aborting."
            )
            return

        try:
            await self.collection.delete_many({})
            logger.info(f"Successfully cleaned up test {self._entity_name} documents")
        except Exception as e:
            logger.error(f"Failed to cleanup test data: {str(e)}")
