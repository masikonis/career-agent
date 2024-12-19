from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from bson import ObjectId

from ..base.types import EntityID
from ..generic.types import SearchableEntity


@dataclass
class Article(SearchableEntity):
    """Article entity representing a news article"""

    title: str
    content: str
    author: str
    source: str
    published_at: datetime
    tags: List[str] = field(default_factory=list)
    url: Optional[str] = None
    id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Define searchable fields and their types
    search_fields: ClassVar[Dict[str, str]] = {
        "title": "text",
        "content": "text",
        "author": "keyword",
        "source": "keyword",
        "tags": "keyword_list",
        "published_at": "date",
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)

        # Convert id back to _id for MongoDB if it exists
        if data["id"] is not None:
            data["_id"] = ObjectId(data.pop("id"))
        else:
            del data["id"]  # Remove id if None

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Article":
        """Create article from dictionary"""
        # Convert MongoDB _id to id
        if "_id" in data:
            data["id"] = str(data.pop("_id"))

        # Convert string dates back to datetime
        for date_field in ["published_at", "created_at", "updated_at"]:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        return cls(**data)

    def get_search_metadata(self) -> Dict[str, Any]:
        """Get metadata for search indexing"""
        return {
            "title": self.title,
            "author": self.author,
            "source": self.source,
            "tags": self.tags,
            "published_at": self.published_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def get_search_text(self) -> str:
        """Get text to be used for search embedding"""
        # Combine title and content for semantic search
        return f"{self.title}\n\n{self.content}"

    def validate(self) -> bool:
        """Validate article data"""
        try:
            if not self.title or not self.content:
                return False

            if not self.author or not self.source:
                return False

            if not isinstance(self.tags, list):
                return False

            if not isinstance(self.published_at, datetime):
                return False

            return True

        except Exception:
            return False


@dataclass
class ArticleFilters:
    """Filters for article search"""

    author: Optional[List[str]] = None
    source: Optional[List[str]] = None
    published_after: Optional[datetime] = None
    published_before: Optional[datetime] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert filters to dictionary format"""
        filters = {}

        if self.author:
            filters["author"] = self.author

        if self.source:
            filters["source"] = self.source

        if self.tags:
            filters["tags"] = {"$in": self.tags}

        if self.published_after or self.published_before:
            date_filter = {}
            if self.published_after:
                date_filter["$gte"] = self.published_after.isoformat()
            if self.published_before:
                date_filter["$lte"] = self.published_before.isoformat()
            filters["published_at"] = date_filter

        return filters
