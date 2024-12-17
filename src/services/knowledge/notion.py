from typing import Dict, List, Optional
from notion_client import Client
from .base import BaseKnowledge

class NotionKnowledge(BaseKnowledge):
    """Notion as a knowledge source"""
    
    def __init__(self, api_key: str):
        self.client = Client(auth=api_key)
    
    async def get_data(self, database_id: str) -> List[Dict]:
        """Get all pages from a database"""
        try:
            response = self.client.databases.query(database_id=database_id)
            return response['results']
        except Exception as e:
            print(f"Error fetching Notion database: {e}")
            return []
