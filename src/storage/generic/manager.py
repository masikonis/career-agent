from typing import Any, Dict, Generic, List, Optional

from src.utils.logger import get_logger

from ..base.exceptions import StorageOperationError
from ..base.types import EntityID
from .interfaces import GenericSearchIndex, GenericStorage
from .types import T


class GenericStorageManager(Generic[T]):
    """Generic storage manager that coordinates storage and search operations"""

    def __init__(
        self,
        storage: GenericStorage[T],
        search_index: GenericSearchIndex[T],
        entity_type: str,
    ):
        self.storage = storage
        self.search_index = search_index
        self.entity_type = entity_type
        self.logger = get_logger(f"{entity_type}_manager")

    async def create(self, entity: T) -> EntityID:
        """Create an entity and index it for search"""
        try:
            # Create in primary storage
            entity_id = await self.storage.create(entity)

            # Index for search
            await self.search_index.index(entity_id, entity)

            return entity_id
        except Exception as e:
            self.logger.error(f"Failed to create {self.entity_type}: {str(e)}")
            raise StorageOperationError(f"{self.entity_type}_create", str(e))

    async def get(self, entity_id: EntityID) -> Optional[T]:
        """Get an entity by ID"""
        try:
            return await self.storage.read(entity_id)
        except Exception as e:
            self.logger.error(f"Failed to get {self.entity_type}: {str(e)}")
            raise StorageOperationError(f"{self.entity_type}_read", str(e))

    async def update(self, entity_id: EntityID, entity: T) -> bool:
        """Update an entity and its search index"""
        try:
            # Update in primary storage
            success = await self.storage.update(entity_id, entity)
            if success:
                # Update search index
                await self.search_index.index(entity_id, entity)
            return success
        except Exception as e:
            self.logger.error(f"Failed to update {self.entity_type}: {str(e)}")
            raise StorageOperationError(f"{self.entity_type}_update", str(e))

    async def delete(self, entity_id: EntityID) -> bool:
        """Delete an entity and remove from search index"""
        try:
            # Delete from primary storage
            success = await self.storage.delete(entity_id)
            if success:
                # Remove from search index
                await self.search_index.delete_from_index(entity_id)
            return success
        except Exception as e:
            self.logger.error(f"Failed to delete {self.entity_type}: {str(e)}")
            raise StorageOperationError(f"{self.entity_type}_delete", str(e))

    async def search(
        self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10
    ) -> List[T]:
        """Search entities"""
        try:
            # Get IDs from search index
            entity_ids = await self.search_index.search(query, filters, limit)

            # Fetch full entities
            entities = []
            for entity_id in entity_ids:
                if entity := await self.get(entity_id):
                    entities.append(entity)

            return entities
        except Exception as e:
            self.logger.error(f"Failed to search {self.entity_type}s: {str(e)}")
            raise StorageOperationError(f"{self.entity_type}_search", str(e))

    async def find_similar(self, entity_id: EntityID, limit: int = 10) -> List[T]:
        """Find similar entities"""
        try:
            similar_ids = await self.search_index.find_similar(entity_id, limit)

            # Fetch full entities
            entities = []
            for similar_id in similar_ids:
                if entity := await self.get(similar_id):
                    entities.append(entity)

            return entities
        except Exception as e:
            self.logger.error(f"Failed to find similar {self.entity_type}s: {str(e)}")
            raise StorageOperationError(f"{self.entity_type}_similar", str(e))
