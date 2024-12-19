from datetime import datetime
from typing import Any, Dict, Generic, List, Optional

from src.utils.logger import get_logger

from ..base.exceptions import EntityNotFoundError, StorageOperationError
from ..base.types import EntityID
from .interfaces import GenericSearchIndex, GenericStorage
from .types import SearchFilter, T


class BaseGenericStorageManager(Generic[T]):
    """Base generic storage manager that handles both storage and search operations"""

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
            # Validate entity
            if not entity.validate():
                raise StorageOperationError(
                    "create", self.entity_type, details="Entity validation failed"
                )

            # Create in primary storage first
            entity_id = await self.storage.create(entity)

            # Create metadata for search indexing
            metadata = {
                **entity.get_search_metadata(),
                "entity_type": self.entity_type,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            # Index for search
            if not await self.search_index.index(entity_id, entity, metadata):
                self.logger.warning(f"Failed to index {self.entity_type} {entity_id}")

            return entity_id

        except Exception as e:
            self.logger.error(f"Failed to create {self.entity_type}: {str(e)}")
            raise StorageOperationError("create", self.entity_type, details=str(e))

    async def get(self, entity_id: EntityID) -> Optional[T]:
        """Get an entity by ID"""
        try:
            entity = await self.storage.read(entity_id)
            if not entity:
                raise EntityNotFoundError(self.entity_type, entity_id)
            return entity

        except EntityNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get {self.entity_type} {entity_id}: {str(e)}")
            raise StorageOperationError("get", self.entity_type, entity_id, str(e))

    async def update(self, entity_id: EntityID, entity: T) -> bool:
        """Update an entity and its search index"""
        try:
            # Validate entity
            if not entity.validate():
                raise StorageOperationError(
                    "update", self.entity_type, entity_id, "Entity validation failed"
                )

            # Update in primary storage
            if not await self.storage.update(entity_id, entity):
                raise EntityNotFoundError(self.entity_type, entity_id)

            # Update search index
            metadata = {
                **entity.get_search_metadata(),
                "entity_type": self.entity_type,
                "updated_at": datetime.now().isoformat(),
            }

            await self.search_index.index(entity_id, entity, metadata)
            return True

        except EntityNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to update {self.entity_type} {entity_id}: {str(e)}"
            )
            raise StorageOperationError("update", self.entity_type, entity_id, str(e))

    async def delete(self, entity_id: EntityID) -> bool:
        """Delete an entity and remove from search index"""
        try:
            # Delete from primary storage
            if not await self.storage.delete(entity_id):
                raise EntityNotFoundError(self.entity_type, entity_id)

            # Remove from search index
            await self.search_index.delete_from_index(entity_id)
            return True

        except EntityNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to delete {self.entity_type} {entity_id}: {str(e)}"
            )
            raise StorageOperationError("delete", self.entity_type, entity_id, str(e))

    async def search(
        self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10
    ) -> List[T]:
        """Search entities with optional filters"""
        try:
            # Get IDs from search index
            entity_ids = await self.search_index.search(query, filters, limit)

            # Fetch full entities
            entities = []
            for entity_id in entity_ids:
                try:
                    if entity := await self.get(entity_id):
                        entities.append(entity)
                except EntityNotFoundError:
                    self.logger.warning(
                        f"Entity {entity_id} found in search index but not in storage"
                    )

            return entities

        except Exception as e:
            self.logger.error(f"Failed to search {self.entity_type}s: {str(e)}")
            raise StorageOperationError("search", self.entity_type, details=str(e))

    async def find_similar(self, entity_id: EntityID, limit: int = 10) -> List[T]:
        """Find similar entities"""
        try:
            # Get similar entity IDs
            similar_ids = await self.search_index.find_similar(entity_id, limit)

            # Fetch full entities
            similar_entities = []
            for similar_id in similar_ids:
                try:
                    if entity := await self.get(similar_id):
                        similar_entities.append(entity)
                except EntityNotFoundError:
                    self.logger.warning(
                        f"Entity {similar_id} found in search index but not in storage"
                    )

            return similar_entities

        except Exception as e:
            self.logger.error(
                f"Failed to find similar {self.entity_type}s for {entity_id}: {str(e)}"
            )
            raise StorageOperationError(
                "find_similar", self.entity_type, entity_id, str(e)
            )

    async def list(self, filter_params: Optional[Dict[str, Any]] = None) -> List[T]:
        """List entities with optional filtering"""
        try:
            return await self.storage.list(filter_params)
        except Exception as e:
            self.logger.error(f"Failed to list {self.entity_type}s: {str(e)}")
            raise StorageOperationError("list", self.entity_type, details=str(e))


class EntityStorageManager(BaseGenericStorageManager[T]):
    """Base class for entity-specific storage managers"""

    def __init__(
        self,
        storage: GenericStorage[T],
        search_index: GenericSearchIndex[T],
        entity_type: str,
    ):
        super().__init__(storage, search_index, entity_type)
        # Allow type-specific references
        self.typed_storage = storage
        self.typed_search = search_index

    async def add_custom_data(
        self, entity_id: EntityID, data: Any, field_name: str
    ) -> bool:
        """Generic method for adding custom data to an entity"""
        try:
            # Update entity in storage
            entity = await self.get(entity_id)
            if not entity:
                raise EntityNotFoundError(self.entity_type, entity_id)

            # Add custom data
            setattr(entity, field_name, data)

            # Update storage
            success = await self.storage.update(entity_id, entity)
            if not success:
                raise StorageOperationError(
                    "add_custom_data", f"Failed to add {field_name}"
                )

            # Update search index
            metadata = {
                **entity.get_search_metadata(),
                "entity_type": self.entity_type,
                "updated_at": datetime.now().isoformat(),
            }
            await self.search_index.index(entity_id, entity, metadata)

            return True

        except Exception as e:
            self.logger.error(f"Failed to add {field_name}: {str(e)}")
            raise StorageOperationError(f"add_{field_name}", str(e))
