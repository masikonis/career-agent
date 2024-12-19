from datetime import datetime
from typing import Any, ClassVar, Dict, Generic, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from src.utils.logger import get_logger

from ..base.exceptions import StorageError
from ..base.types import EntityID, T
from .interfaces import GenericStorage


class MongoOperators:
    """MongoDB operator constants for use across all MongoDB implementations"""

    # Comparison
    EQ = "$eq"
    GT = "$gt"
    GTE = "$gte"
    LT = "$lt"
    LTE = "$lte"
    NE = "$ne"
    IN = "$in"
    NIN = "$nin"

    # Logical
    AND = "$and"
    OR = "$or"
    NOT = "$not"
    NOR = "$nor"

    # Array
    ALL = "$all"
    ELEM_MATCH = "$elemMatch"
    SIZE = "$size"

    # Update
    SET = "$set"
    UNSET = "$unset"
    INC = "$inc"
    ADD_TO_SET = "$addToSet"
    PUSH = "$push"
    PULL = "$pull"
    PULL_ALL = "$pullAll"
    POP = "$pop"

    # Array Update Modifiers
    EACH = "$each"
    POSITION = "$position"
    SLICE = "$slice"
    SORT = "$sort"


class MongoDBStorage(GenericStorage[T]):
    """Generic MongoDB storage implementation"""

    def __init__(
        self,
        connection_string: str,
        database: str,
        collection: str,
        is_test: bool = False,
    ):
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client[database]
        self.collection_name = f"test_{collection}" if is_test else collection
        self.collection: AsyncIOMotorCollection = self.db[self.collection_name]
        self.is_test = is_test
        self.logger = get_logger(f"mongodb_{collection}")

    async def create(self, entity: T) -> EntityID:
        """Create a new entity"""
        try:
            doc = entity.to_dict()
            result = self.collection.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Failed to create entity: {str(e)}")
            raise StorageError(f"Entity creation failed: {str(e)}")

    async def read(self, entity_id: EntityID) -> Optional[T]:
        """Read an entity by ID"""
        try:
            doc = self.collection.find_one({"_id": ObjectId(entity_id)})
            if doc:
                # Convert _id to string
                doc["id"] = str(doc.pop("_id"))
                return self.entity_class.from_dict(doc)
            return None
        except Exception as e:
            self.logger.error(f"Failed to read entity: {str(e)}")
            raise StorageError(f"Entity read failed: {str(e)}")

    async def update(self, entity_id: EntityID, entity: T) -> bool:
        """Update an existing entity"""
        try:
            doc = entity.to_dict()
            # Don't update the ID field
            if "id" in doc:
                del doc["id"]

            result = self.collection.update_one(
                {"_id": ObjectId(entity_id)}, {"$set": doc}
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Failed to update entity: {str(e)}")
            raise StorageError(f"Entity update failed: {str(e)}")

    async def delete(self, entity_id: EntityID) -> bool:
        """Delete an entity"""
        try:
            result = self.collection.delete_one({"_id": ObjectId(entity_id)})
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Failed to delete entity: {str(e)}")
            raise StorageError(f"Entity deletion failed: {str(e)}")

    async def list(self, filter_params: Optional[Dict[str, Any]] = None) -> List[T]:
        """List entities with optional filtering"""
        try:
            # Convert filter params if needed
            mongo_filter = {}
            if filter_params:
                mongo_filter = filter_params.copy()
                # Handle any special filter conversions here
                # For example, date ranges, enum values, etc.

            cursor = self.collection.find(mongo_filter)
            entities = []

            async for doc in cursor:
                # Convert _id to string
                doc["id"] = str(doc.pop("_id"))
                entities.append(self.entity_class.from_dict(doc))

            return entities
        except Exception as e:
            self.logger.error(f"Failed to list entities: {str(e)}")
            raise StorageError(f"Entity listing failed: {str(e)}")

    async def cleanup_test_data(self):
        """Clean up all test data - should only be used in test environment"""
        if self.db.name.endswith("-test"):
            self.collection.delete_many({})
            self.logger.info(f"Cleaned up test data from {self.collection.name}")
        else:
            raise StorageError("Cleanup can only be performed on test database")
