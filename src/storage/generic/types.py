from datetime import datetime
from typing import Any, ClassVar, Dict, List, Protocol, TypeVar


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
        """
        Get metadata for search indexing.
        Should return a dictionary of searchable fields and their values.
        """
        pass

    def get_search_text(self) -> str:
        """
        Get text to be used for search embedding.
        Should return a concatenated string of all searchable text fields.
        """
        pass

    def validate(self) -> bool:
        """
        Validate entity data.
        Returns True if entity is valid, False otherwise.
        """
        pass


T = TypeVar("T", bound=SearchableEntity)


# Common filter types
class FilterOperator:
    """Common filter operators"""

    EQ = "eq"  # equals
    NE = "ne"  # not equals
    GT = "gt"  # greater than
    GTE = "gte"  # greater than or equal
    LT = "lt"  # less than
    LTE = "lte"  # less than or equal
    IN = "in"  # in array
    NIN = "nin"  # not in array
    CONTAINS = "contains"  # contains string
    STARTS_WITH = "starts_with"  # starts with string
    ENDS_WITH = "ends_with"  # ends with string


class SearchFilter:
    """Base class for search filters"""

    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary format"""
        return {"field": self.field, "operator": self.operator, "value": self.value}
