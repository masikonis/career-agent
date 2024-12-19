from typing import Generic, List, Optional

from src.utils.logger import get_logger

from ..base.exceptions import StorageOperationError, StorageSyncError
from ..base.interfaces import BaseStorage, SearchIndex
from ..base.types import EntityID, Metadata, T

logger = get_logger(__name__)


class BaseStorageManager(Generic[T]):
    """
    Coordinates operations between primary storage and search index.
    Ensures consistency between the two systems.
    """

    def __init__(self, storage: BaseStorage[T], search_index: SearchIndex[T]):
        self.storage = storage
        self.search_index = search_index

    async def create(self, entity: T) -> EntityID:
        """Create entity in storage and index it for search"""
        try:
            # First, create in primary storage
            entity_id = await self.storage.create(entity)

            # Then, index for search
            metadata = self._create_metadata(entity)
            await self.search_index.index(entity_id, entity, metadata)

            return entity_id

        except Exception as e:
            logger.error(f"Failed to create entity: {str(e)}")
            # TODO: Implement rollback mechanism
            raise StorageOperationError("create", str(e))

    async def get(self, entity_id: EntityID) -> Optional[T]:
        """Retrieve entity by ID"""
        return await self.storage.read(entity_id)

    async def search(self, query: str, limit: int = 10) -> List[T]:
        """Search for entities"""
        try:
            # First, get IDs from search index
            entity_ids = await self.search_index.search(query, limit)

            # Then, get full entities from storage
            entities = []
            for entity_id in entity_ids:
                if entity := await self.get(entity_id):
                    entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise StorageOperationError("search", str(e))

    def _create_metadata(self, entity: T) -> Metadata:
        """Create metadata for an entity"""
        # To be implemented by specific managers
        raise NotImplementedError
