from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseKnowledge(ABC):
    """Base class for knowledge source services"""
    
    @abstractmethod
    async def get_data(self, *args, **kwargs) -> Any:
        """Get data from the knowledge source"""
        pass
