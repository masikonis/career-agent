from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStore(ABC):
    """Base class for all vector stores"""
    
    @abstractmethod
    async def add_item(self, item_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Add an item to the vector store
        
        Args:
            item_id: Unique identifier for the item
            content: Main content to be vectorized
            metadata: Additional information about the item
        """
        pass

    @abstractmethod
    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an item by its ID
        
        Args:
            item_id: Unique identifier for the item
        
        Returns:
            Item data if found, None otherwise
        """
        pass

    @abstractmethod
    async def update_item(self, item_id: str, metadata: Dict[str, Any]) -> bool:
        """Update an item's metadata
        
        Args:
            item_id: Unique identifier for the item
            metadata: New metadata to update
            
        Returns:
            True if update successful, False otherwise
        """
        pass

    @abstractmethod
    async def find_similar(self, content: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find similar items based on content
        
        Args:
            content: Content to compare against
            n_results: Number of similar items to return
            
        Returns:
            List of similar items with their similarity scores
        """
        pass

    @abstractmethod
    async def delete_item(self, item_id: str) -> bool:
        """Delete an item from the store
        
        Args:
            item_id: Unique identifier for the item
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass
