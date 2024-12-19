from typing import Any, Dict, List, Optional, Type

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

from src.utils.logger import get_logger

from ..base.exceptions import StorageError
from ..base.types import EntityID
from .interfaces import GenericStorage
from .types import T


class MongoDBStorage(GenericStorage[T]):
    """Generic MongoDB storage implementation"""

    def __init__(
        self,
        config: Dict,
        collection_name: str,
        entity_class: Type[T],
        is_test: bool = False,
    ):
        try:
            self.client = MongoClient(config["MONGODB_URI"])
            db_name = (
                f"{config['MONGODB_DB_NAME']}-test"
                if is_test
                else config["MONGODB_DB_NAME"]
            )
            self.db: Database = self.client[db_name]
            self.collection = self.db[collection_name]
            self.entity_class = entity_class
            self.logger = get_logger(f"mongodb_{collection_name}")

            # Create indexes based on entity's search_fields
            if hasattr(entity_class, "search_fields"):
                for field in entity_class.search_fields:
                    self.collection.create_index(field)

            self.logger.info(f"Connected to MongoDB collection: {collection_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize MongoDB connection: {str(e)}")
            raise StorageError(f"MongoDB initialization failed: {str(e)}")

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
