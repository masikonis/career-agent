from abc import ABC, abstractmethod
from typing import Dict, List

class BaseKnowledge(ABC):
    """Base class for knowledge source services"""
    
    @abstractmethod
    async def get_page_content(self, page_id: str) -> Dict:
        """Get page content from the knowledge source"""
        pass
    
    @abstractmethod
    async def get_capabilities(self, database_id: str) -> List[Dict]:
        """Get capabilities data from the knowledge source"""
        pass
