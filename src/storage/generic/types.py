from datetime import datetime
from typing import Any, ClassVar, Dict, Protocol, TypeVar


class BaseEntity(Protocol):
    """Base protocol that all entities must implement"""

    id: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary"""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEntity":
        """Create entity from dictionary"""
        pass


class SearchableEntity(BaseEntity, Protocol):
    """Protocol for entities that can be searched"""

    search_fields: ClassVar[Dict[str, str]]  # Maps field names to their search types

    def get_search_metadata(self) -> Dict[str, Any]:
        """Get metadata for search indexing"""
        pass


T = TypeVar("T", bound=SearchableEntity)
