from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, Optional, TypeVar, Dict, List

from .types import EntityID, Metadata

# Generic type for any entity
T = TypeVar('T')

class BaseStorage(ABC, Generic[T]):
    """
    Base interface for all storage operations.
    Handles basic CRUD operations for any entity type.
    """
    
    @abstractmethod
    async def create(self, entity: T) -> EntityID:
        """Create a new entity in storage"""
        pass

    @abstractmethod
    async def read(self, entity_id: EntityID) -> Optional[T]:
        """Retrieve an entity by ID"""
        pass

    @abstractmethod
    async def update(self, entity_id: EntityID, entity: T) -> bool:
        """Update an existing entity"""
        pass

    @abstractmethod
    async def delete(self, entity_id: EntityID) -> bool:
        """Delete an entity"""
        pass

class SearchIndex(ABC, Generic[T]):
    """
    Base interface for search operations.
    Handles semantic search and indexing.
    """

    @abstractmethod
    async def index(self, entity_id: EntityID, entity: T, metadata: Metadata) -> bool:
        """Index an entity for search"""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[EntityID]:
        """Search for entities and return their IDs"""
        pass

    @abstractmethod
    async def delete_from_index(self, entity_id: EntityID) -> bool:
        """Remove an entity from the search index"""
        pass
