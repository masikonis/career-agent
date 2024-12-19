from abc import ABC, abstractmethod
from typing import Dict, List


class ProfileDataSource(ABC):
    """Abstract base class for profile data sources"""

    @abstractmethod
    async def get_strategy(self) -> Dict[str, str]:
        """Get strategy content"""
        pass

    @abstractmethod
    async def get_capabilities(self) -> List[Dict]:
        """Get capabilities data"""
        pass
