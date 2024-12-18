from typing import List, Dict, Optional
import re
from src.utils.logger import get_logger
from .base import ProfileDataSource

logger = get_logger(__name__)

class ProfileManager:
    """Manages access to profile data with advanced querying and analysis capabilities"""
    
    def __init__(self, data_source: ProfileDataSource):
        self.data_source = data_source
        logger.info("ProfileManager initialized")
    
    async def get_strategy(self) -> Dict[str, str]:
        """Get the strategy content from the data source"""
        return await self.data_source.get_strategy()
    
    async def get_capabilities(self) -> List[Dict]:
        """Get all capabilities"""
        return await self.data_source.get_capabilities()
    
    async def get_capabilities_by_category(self, category: str) -> List[Dict]:
        """Get capabilities filtered by category"""
        capabilities = await self.get_capabilities()
        return [cap for cap in capabilities if cap['category'].lower() == category.lower()]

    async def get_capabilities_by_level(self, level: str) -> List[Dict]:
        """Get capabilities filtered by level"""
        logger.debug(f"Getting capabilities by level: {level}")
        capabilities = await self.get_capabilities()
        return [cap for cap in capabilities if cap['level'].lower() == level.lower()]
