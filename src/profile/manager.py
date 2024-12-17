from typing import List, Dict, Optional
from .base import ProfileDataSource

class ProfileManager:
    """Manages access to profile data through a configured data source"""
    
    def __init__(self, data_source: ProfileDataSource):
        self.data_source = data_source
    
    async def get_capabilities(self) -> List[Dict]:
        """Get all capabilities"""
        return await self.data_source.get_capabilities()
    
    async def get_capabilities_by_category(self, category: str) -> List[Dict]:
        """Get capabilities filtered by category"""
        capabilities = await self.get_capabilities()
        return [cap for cap in capabilities if cap['category'].lower() == category.lower()]
    
    async def get_capabilities_by_level(self, level: str) -> List[Dict]:
        """Get capabilities filtered by level"""
        capabilities = await self.get_capabilities()
        return [cap for cap in capabilities if cap['level'].lower() == level.lower()]
    
    async def get_top_capabilities(self, limit: int = 5) -> List[Dict]:
        """Get top capabilities (assuming Expert/Advanced levels indicate top skills)"""
        capabilities = await self.get_capabilities()
        top_levels = ['Expert', 'Advanced']
        top_caps = [cap for cap in capabilities if cap['level'] in top_levels]
        limit = int(limit) if isinstance(limit, (int, float, str)) and str(limit).isdigit() else 5
        return sorted(top_caps, key=lambda x: ['Expert', 'Advanced'].index(x['level']))[:limit]
    
    async def search_capabilities(self, query: str) -> List[Dict]:
        """Search capabilities by name or content"""
        capabilities = await self.get_capabilities()
        query = query.lower()
        return [
            cap for cap in capabilities 
            if query in cap['name'].lower() 
            or query in cap['experience'].lower()
        ]
