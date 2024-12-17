from typing import List, Dict
from notion_client import Client

class NotionKnowledge:
    def __init__(self, api_key: str):
        self.client = Client(auth=api_key)
    
    async def get_data(self, database_id: str) -> List[Dict]:
        try:
            response = self.client.databases.query(database_id=database_id)
            
            # Transform the response to a simpler format
            capabilities = []
            for page in response['results']:
                props = page['properties']
                capability = {
                    'name': props['Name']['title'][0]['text']['content'],
                    'category': props['Category']['select']['name'],
                    'level': props['Level']['select']['name'],
                    'experience': props['Experience']['rich_text'][0]['text']['content']
                }
                capabilities.append(capability)
            
            return capabilities
            
        except Exception as e:
            print(f"Error fetching Notion database: {e}")
            raise
