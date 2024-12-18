from abc import ABC, abstractmethod
from typing import List, Dict

class ProfileDataSource(ABC):
    """Abstract base class for profile data sources"""
    
    @abstractmethod
    async def get_strategy(self) -> Dict:
        """Get strategy data"""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[Dict]:
        """Get capabilities data"""
        pass
