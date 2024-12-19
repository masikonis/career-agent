from datetime import datetime
from typing import Any, Dict, NewType, TypeVar

# Define the generic type variable
T = TypeVar("T")

# Type aliases for clarity and type safety
EntityID = NewType("EntityID", str)


class Metadata(Dict[str, Any]):
    """Base metadata type that all entities will include"""

    created_at: datetime
    updated_at: datetime
    entity_type: str
