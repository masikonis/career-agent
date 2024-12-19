from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional

from ..base.types import EntityID, Metadata
from .types import T


class GenericStorage(ABC, Generic[T]):
    """Generic storage interface with basic CRUD operations"""

    @abstractmethod
    async def create(self, entity: T) -> EntityID:
        """Create a new entity"""
        pass

    @abstractmethod
    async def read(self, entity_id: EntityID) -> Optional[T]:
        """Read an entity by ID"""
        pass

    @abstractmethod
    async def update(self, entity_id: EntityID, entity: T) -> bool:
        """Update an existing entity"""
        pass

    @abstractmethod
    async def delete(self, entity_id: EntityID) -> bool:
        """Delete an entity"""
        pass

    @abstractmethod
    async def list(self, filter_params: Optional[Dict[str, Any]] = None) -> List[T]:
        """List entities with optional filtering"""
        pass


class GenericSearchIndex(ABC, Generic[T]):
    """Generic search index interface"""

    @abstractmethod
    async def index(self, entity_id: EntityID, entity: T) -> bool:
        """Index an entity for search"""
        pass

    @abstractmethod
    async def search(
        self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10
    ) -> List[EntityID]:
        """Search entities"""
        pass

    @abstractmethod
    async def delete_from_index(self, entity_id: EntityID) -> bool:
        """Remove entity from search index"""
        pass

    @abstractmethod
    async def find_similar(
        self, entity_id: EntityID, limit: int = 10
    ) -> List[EntityID]:
        """Find similar entities"""
        pass
