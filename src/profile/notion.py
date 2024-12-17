from typing import List, Dict
from ..services.knowledge.notion import NotionKnowledge
from .base import ProfileDataSource

class NotionProfileSource(ProfileDataSource):
    """Notion-specific implementation of profile data source"""
    
    def __init__(self, notion_client: NotionKnowledge):
        self.notion = notion_client
        self.capabilities_db = "15f4d9e70cb080eaa0a9d34cd61f2bd3"
    
    async def get_capabilities(self) -> List[Dict]:
        """Get capabilities from Notion database"""
        return await self.notion.get_data(self.capabilities_db)
